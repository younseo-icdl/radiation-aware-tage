"""Recovery in an observed suffix, with recurrence and cancellation explicit.

Logical replay observations cannot supply CPU timing. Missing/alignment gaps
are never converted to zero distance, and cumulative loss need not return to
zero for subsequent excess time to stop.
"""
from dataclasses import dataclass
from math import isfinite
import argparse
import csv
import json
from pathlib import Path


@dataclass
class RecoverySeries:
    pre_fault_observed: bool = True
    first_affected: int | None = None
    first_zero: int | None = None
    last_nonzero: int | None = None
    stable_start: int | None = None
    last_observation: int | None = None
    previous_value: int | None = None
    recurrence_count: int = 0
    aligned_observations: int = 0
    had_gap: bool = False
    first_zero_interval: tuple[int, int] | None = None
    _gap_since_value: bool = False

    def observe(self, ordinal, value):
        if self.last_observation is not None and ordinal <= self.last_observation:
            raise ValueError('observation ordinals must strictly increase')
        self.last_observation = ordinal
        if value is None:
            self.had_gap = self._gap_since_value = True
            self.stable_start = None
            return
        if value < 0:
            raise ValueError('state distance must be nonnegative')
        self.aligned_observations += 1
        if value:
            if self.first_affected is None:
                self.first_affected = ordinal
            if self.previous_value == 0 and (self.first_zero is not None or self.first_zero_interval is not None):
                self.recurrence_count += 1
            self.last_nonzero = ordinal
            self.stable_start = None
        elif self.first_affected is not None:
            if self.first_zero is None and self.first_zero_interval is None:
                if self._gap_since_value:
                    self.first_zero_interval = (self.last_nonzero, ordinal)
                else:
                    self.first_zero = ordinal
            if self.stable_start is None:
                self.stable_start = ordinal
        self.previous_value = value
        self._gap_since_value = False

    def summary(self):
        if not self.aligned_observations:
            status = 'NA_ALIGNMENT'
        elif self.first_affected is None:
            status = 'NA_ALIGNMENT' if self.had_gap else 'NOT_AFFECTED'
        elif (self._gap_since_value or self.previous_value != 0 or self.stable_start is None
              or self.last_observation <= self.stable_start):
            status = 'RIGHT_CENSORED'
        else:
            status = 'RECOVERED_WITHIN_OBSERVED_SUFFIX'
        observed_status = status
        if not self.pre_fault_observed:
            status = 'PRE_ROI_HISTORY_UNOBSERVED'
        return {'first_affected': self.first_affected if self.pre_fault_observed else None,
                'first_observed_nonzero': self.first_affected,
                'first_zero': self.first_zero if self.pre_fault_observed else None,
                'first_observed_zero_after_difference': self.first_zero,
                'last_nonzero': self.last_nonzero,
                'stable_to_horizon_start': self.stable_start,
                'recurrence_count': self.recurrence_count,
                'recurrence_count_is_lower_bound': self.had_gap or not self.pre_fault_observed,
                'had_recurrence': bool(self.recurrence_count),
                'observation_end': self.last_observation,
                'recovery_status': status, 'observed_suffix_status': observed_status,
                'pre_roi_history_observed': self.pre_fault_observed,
                'had_alignment_gap': self.had_gap,
                'first_zero_interval': self.first_zero_interval,
                'interval_censor_lower': self.first_zero_interval[0] if self.first_zero_interval else None,
                'interval_censor_upper': self.first_zero_interval[1] if self.first_zero_interval else None}


def timing_windows(checkpoints, window_size=1024, required_windows=3, epsilon=0):
    """Use paired exact-time checkpoints, not a miss-count penalty.

    Each checkpoint has branch_id, fault_time, clean_time, and optional
    harmful/helpful/prediction_differences since the preceding checkpoint.
    Checkpoints may be finer than a full window. No interpolation fills gaps.
    """
    if window_size <= 0 or required_windows <= 0 or epsilon < 0:
        raise ValueError('invalid recovery window rule')
    points = list(checkpoints)
    if len(points) < 2:
        return {'recovery_status': 'INSUFFICIENT_OBSERVATION', 'windows': []}
    for point in points:
        if not all(key in point for key in ('branch_id', 'fault_time', 'clean_time')):
            raise ValueError('paired exact-time checkpoints are required')
        if not all(isfinite(point[key]) for key in ('branch_id', 'fault_time', 'clean_time')):
            raise ValueError('checkpoint values must be finite')
        if point.get('alignment_status', 'ALIGNED') != 'ALIGNED':
            raise ValueError('unaligned checkpoints cannot supply paired timing')
    rows, segments = [], []
    start = previous = points[0]

    def append_window(point, full):
        excess = sum(delta for delta, _ in segments)
        positive = sum(max(delta, 0) for delta, _ in segments)
        negative = sum(min(delta, 0) for delta, _ in segments)
        rows.append({'window_index': len(rows), 'start_branch_id': start['branch_id'],
                     'end_branch_id': point['branch_id'], 'full_window': full,
                     'sampling_gap': point['branch_id']-start['branch_id'] > window_size,
                     'subwindow_observations': len(segments),
                     'incremental_excess_time': excess,
                     'cumulative_time_gap': point['fault_time']-point['clean_time'],
                     'subwindow_positive_excess_sum': positive,
                     'subwindow_negative_excess_sum': negative,
                     'net_zero_within_window': abs(excess) <= epsilon and positive > epsilon
                                             and negative < -epsilon,
                     'harmful_count': sum(p.get('harmful', 0) for _, p in segments),
                     'helpful_count': sum(p.get('helpful', 0) for _, p in segments),
                     'prediction_differences': sum(p.get('prediction_differences', 0) for _, p in segments)})

    for point in points[1:]:
        if point['branch_id'] <= previous['branch_id']:
            raise ValueError('checkpoint branch IDs must strictly increase')
        fault = point['fault_time'] - previous['fault_time']
        clean = point['clean_time'] - previous['clean_time']
        if fault < 0 or clean < 0:
            raise ValueError('execution time must not go backwards')
        segments.append((fault-clean, point))
        previous = point
        span = point['branch_id'] - start['branch_id']
        if span < window_size:
            continue
        # A missing boundary cannot be silently interpolated into a full window.
        full = span == window_size
        append_window(point, full)
        start, segments = point, []
    trailing_incomplete = bool(segments)
    if segments:
        append_window(previous, False)
    eligible = []
    for row in rows:
        eligible.append(not row['sampling_gap']
                        and (not row['full_window'] or row['subwindow_observations'] > 1)
                        and abs(row['incremental_excess_time']) <= epsilon
                        and row['subwindow_positive_excess_sum'] <= epsilon
                        and abs(row['subwindow_negative_excess_sum']) <= epsilon
                        and not row['harmful_count'] and not row['helpful_count']
                        and not row['prediction_differences'])
    suffix = 0
    for row, good in reversed(list(zip(rows, eligible))):
        if not good:
            break
        suffix += int(row['full_window'])
    if sum(r['full_window'] and r['subwindow_observations'] > 1 for r in rows) < required_windows:
        status = 'INSUFFICIENT_OBSERVATION'
    elif suffix >= required_windows:
        status = 'RECOVERED_WITHIN_OBSERVED_SUFFIX'
    else:
        status = 'RIGHT_CENSORED'
    positive_windows = [r['window_index'] for r in rows
                        if r['subwindow_positive_excess_sum'] > epsilon]
    changing_windows = [r['window_index'] for r in rows
                        if abs(r['incremental_excess_time']) > epsilon]
    return {'recovery_status': status, 'windows': rows,
            'last_positive_excess_window': positive_windows[-1] if positive_windows else None,
            'last_nonzero_excess_window': changing_windows[-1] if changing_windows else None,
            'window_size': window_size, 'epsilon': epsilon,
            'required_consecutive_windows': required_windows,
            'trailing_incomplete': trailing_incomplete}


def summarize_replay(directory):
    """Summarize measured callback distances; leave missing CPU time as N/A."""
    directory = Path(directory)
    case = json.loads((directory/'case.json').read_text())
    if case['trace_kind'] != 'COMMITTED_ONLY_REPLAY':
        raise ValueError('this reader accepts committed replay only')
    with (directory/'STATE_DISTANCE_TIMESERIES.csv').open(newline='') as source:
        reader = csv.DictReader(source)
        rows = list(reader)
    if not rows or any(None in row for row in rows):
        raise ValueError('empty or malformed distance timeline')
    coordinates = {int(row['callback_ordinal']): row for row in rows}
    components = ['raw_distance', 'path_distance', 'nonspec_path_distance', 'head_difference',
                  'fold_invariant_distance', 'fold_reference_distance', 'learning_field_differences',
                  'bimodal_prediction_fields', 'bimodal_hysteresis_fields', 'tagged_counter_fields',
                  'stored_tag_fields', 'useful_fields', 'chooser_fields', 'allocator_difference',
                  'rng_difference', 'index_mismatch', 'query_tag_mismatch', 'provider_mismatch',
                  'prediction_difference', 'harmful', 'helpful']
    components += [name for name in rows[0] if name.endswith(('_invariant_distance', '_reference_distance'))
                   and name.startswith('folded:')]
    components += [name for name in rows[0] if name.startswith(('index_mismatch_bank_', 'query_tag_mismatch_bank_'))]
    summaries = []
    for name in components:
        series = RecoverySeries(pre_fault_observed=case['pre_fault_observed'])
        for row in rows:
            value = row[name]
            if value == 'NOT_APPLICABLE':
                continue  # No lookup occurred; this is not a fake matching access.
            series.observe(int(row['callback_ordinal']), int(value))
        result = series.summary()
        result['state_component'] = name
        result['run_id'] = directory.name
        result['trace_kind'] = case['trace_kind']
        for milestone in ('first_zero', 'last_nonzero', 'stable_to_horizon_start'):
            coordinate = coordinates.get(result[milestone], {})
            for key in ('branch_id', 'history_updates_since_fault', 'conditional_history_transitions'):
                result[milestone+'_'+key] = coordinate.get(key)
        summaries.append(result)
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='one tage-causal output directory')
    parser.add_argument('--output', type=Path, required=True, help='fresh analysis directory')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output exists; use a fresh directory')
    summaries = summarize_replay(args.directory)
    args.output.mkdir(parents=True)
    with (args.output/'RECOVERY_TIMELINE.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    with (args.output/'RECOVERY_WINDOWS.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['run_id', 'trace_kind', 'recovery_status', 'reason'])
        writer.writeheader()
        writer.writerow({'run_id': args.directory.name, 'trace_kind': 'COMMITTED_ONLY_REPLAY',
                         'recovery_status': 'NOT_APPLICABLE',
                         'reason': 'No paired CPU times were observed; no miss penalty substitutes for CPU time.'})
    print(json.dumps({'run_id': args.directory.name, 'state_components': len(summaries),
                      'CPU_timing': 'NOT_APPLICABLE'}))


if __name__ == '__main__':
    main()
