"""Check a native history trace against the registered datapath's edge interface."""
import argparse
import csv
from collections import Counter, OrderedDict
import json
from pathlib import Path


def check_trace(stream, period=None):
    header = stream.readline().strip()
    if not header.startswith('# capture_end_tick='):
        raise ValueError('missing capture-end boundary')
    end = int(header.split('=', 1)[1])
    reader = csv.DictReader(stream)
    if end <= 0 or reader.fieldnames != ['tick', 'operation', 'owner', 'value', 'auxiliary']:
        raise ValueError('invalid activity schema')
    if period is not None and (period <= 0 or end % period):
        raise ValueError('capture end must be on the clock grid')
    allocated = set()
    appended = OrderedDict()
    totals = Counter()
    conflicts = Counter()
    first_conflict = {}
    peak = Counter()
    ordering = Counter({key: 0 for key in (
        'query_after_undo', 'query_after_append', 'append_after_query',
        'query_after_query_then_append',
    )})
    frame = Counter()
    tick = -1
    ready = None
    pending_query = None
    response_needs_append = False
    staged = Counter()
    response_latencies = Counter()

    def conflict(key):
        conflicts[key] += 1
        first_conflict.setdefault(key, tick)

    for row in reader:
        at, owner, value, extra = (int(row[k]) for k in ('tick', 'owner', 'value', 'auxiliary'))
        op = row['operation']
        if not 0 <= at < end or at < tick:
            raise ValueError('trace tick out of sequence or outside capture window')
        if period is not None and at % period:
            raise ValueError('operation is off the clock grid')
        if at != tick:
            if response_needs_append:
                raise ValueError('staged row response had no same-tick append')
            tick, frame = at, Counter()
        if ready is not None and tick >= ready and op != 'publish':
            raise ValueError('work crossed a pending publication deadline')
        if ready is not None and op in ('append', 'query', 'undo', 'query_request',
                                        'hash_capture', 'row_response'):
            raise ValueError('work entered quiescent service')
        if op == 'query':
            if owner or extra or not 0 <= value < 2**64:
                raise ValueError('invalid query record')
            ordering['query_after_undo'] += bool(frame['undo'])
            ordering['query_after_append'] += bool(frame['append'])
            ordering['query_after_query_then_append'] += bool(frame['append_after_query'])
        elif op in ('query_request', 'hash_capture', 'row_response', 'query_cancel'):
            if not 0 < owner < 2**32 or extra or not 0 <= value < 2**64:
                raise ValueError('invalid staged query operand')
            if op == 'query_request':
                if pending_query is not None or frame['append'] or frame['undo'] or frame['row_response']:
                    raise ValueError('staged request overlaps another request or history work')
                pending_query = {'token': owner, 'pc': value, 'start': tick, 'invalidated': False}
            elif pending_query is None or (owner, value) != (pending_query['token'], pending_query['pc']):
                raise ValueError('staged event has no matching request')
            elif op == 'hash_capture':
                if 'capture' in pending_query or pending_query['start'] >= tick or pending_query['invalidated']:
                    raise ValueError('hash capture was early, stale, or repeated')
                if period is not None and tick - pending_query['start'] != period:
                    raise ValueError('hash capture missed its registered edge')
                pending_query['capture'] = tick
            elif op == 'row_response':
                if pending_query.get('capture', tick) >= tick or pending_query['invalidated'] or response_needs_append:
                    raise ValueError('row response preceded readiness or used an invalidated hash')
                response_latencies[tick - pending_query['capture']] += 1
                response_needs_append = True
                pending_query = None
            else:
                staged['canceled_after_capture' if 'capture' in pending_query else 'canceled_before_capture'] += 1
                staged['canceled_after_same_tick_capture_and_mutation'] += pending_query.get(
                    'same_tick_invalidation', False)
                pending_query = None
        elif op == 'append':
            if owner <= 0 or owner in appended or value not in (0, 1) or extra not in (0, 1):
                raise ValueError('invalid or duplicate owner append')
            allocated.add(owner)
            appended[owner] = None
            response_needs_append = False
            if frame['query']:
                frame['append_after_query'] += 1
                ordering['append_after_query'] += 1
        elif op == 'undo':
            if value != 1 or extra or not appended or next(reversed(appended)) != owner:
                raise ValueError('undo did not reference the youngest appended owner')
            appended.popitem()
            if frame['append'] or frame['query']:
                conflict('undo_after_append_or_query')
        elif op == 'release':
            if value or extra or owner not in allocated:
                raise ValueError('release without allocated owner')
            allocated.remove(owner)
            appended.pop(owner, None)
        elif op == 'service_start':
            if owner or ready is not None or allocated or pending_query is not None or value <= tick or extra <= 0:
                raise ValueError('invalid service start or occupied owners')
            ready = value
        elif op == 'publish':
            if owner or value or extra or tick != ready or allocated:
                raise ValueError('invalid publication boundary')
            ready = None
        else:
            raise ValueError('unknown activity operation: '+op)
        if op in ('append','undo') and pending_query is not None:
            pending_query['invalidated'] = True
            if pending_query.get('capture') == tick:
                pending_query['same_tick_invalidation'] = True
        frame[op] += 1
        totals[op] += 1
        peak[op] = max(peak[op], frame[op])
        peak['owners'] = max(peak['owners'], len(allocated))
        if frame[op] == {'query': 3, 'append': 4, 'undo': 513}.get(op, 0):
            conflict(op+'_issue_width')
        state_work = ('append', 'query', 'undo', 'hash_capture', 'row_response')
        if (op == 'publish' or op in state_work) and frame['publish'] and any(frame[x] for x in state_work):
            conflict('publication_shares_edge_with_work')
        if len(allocated) == 513:
            conflict('owner_capacity')
    if not totals:
        raise ValueError('no captured history operations')
    if response_needs_append:
        raise ValueError('staged trace ended before a recorded response appended')
    if totals['query_request'] and totals['query']:
        raise ValueError('mixed staged and unstaged query records')
    result = {'scope': 'captured clean operations and conservative undo-first edge grouping',
            'capture_end_tick_exclusive': end, 'last_observed_operation_tick': tick,
            'totals': totals, 'peak_per_tick': peak, 'conflicting_operations': conflicts,
            'same_tick_ordering': ordering,
            'first_conflict_tick': first_conflict, 'pending_service_at_capture_end': ready,
            'status': 'REQUIRES_SCHEDULING' if conflicts else 'NO_OBSERVED_EDGE_CONFLICT',
            'cpu_timing_qualified': False}
    if totals['query_request']:
        result['staged_queries'] = {
            **staged, 'pending_at_capture_end': pending_query,
            'row_response_capture_latency_tick_counts': dict(sorted(response_latencies.items())),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--period-ticks', type=int)
    args = parser.parse_args()
    try:
        with args.trace.open(newline='') as source:
            result = check_trace(source, args.period_ticks)
        with args.output.open('x') as output:
            json.dump(result, output, indent=2)
            output.write('\n')
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
