"""Replay staged CPU ownership and history timing with observed append bits.

Returned rows are represented by a bimodal response matching the recorded
speculative direction. This replays interface behavior, not table activity.
"""
import argparse
import csv
import heapq
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path

from .history_activity import check_trace


@dataclass
class Edge:
    request: int = 0
    pc: int = 0
    query_owner: int = 0
    cancel: bool = False
    response: int = 0
    response_bit: int = 0
    undo: int = 0
    restore: int = 0
    appends: list = field(default_factory=list)
    response_append: tuple | None = None


def rtl_token(token):
    # A token is unique among the outstanding requests in this replay.
    return (token - 1) % 65535 + 1


def replay(stream, period):
    summary = check_trace(stream, period)
    conflicts = set(summary['conflicting_operations']) - {'publication_shares_edge_with_work'}
    if 'staged_queries' not in summary or conflicts or period < 2:
        raise ValueError('trace does not fit the staged history interface')
    end = summary['capture_end_tick_exclusive']
    stream.seek(0)
    stream.readline()
    edges = defaultdict(Edge)
    service, publications = set(), set()
    slots = {}
    free = list(range(512))
    captured = None
    for tick, rows in groupby(csv.DictReader(stream), key=lambda row: int(row['tick'])):
        response = None
        released = []
        for row in rows:
            operation = row['operation']
            owner, value, extra = (int(row[k]) for k in ('owner', 'value', 'auxiliary'))
            if operation == 'hash_capture':
                captured = edges[tick]
                captured.request = rtl_token(owner)
                captured.pc = value & 0xffffffff
            elif operation == 'query_cancel':
                if captured is not None:
                    edges[tick].cancel = True
                    captured = None
            elif operation == 'row_response':
                response = captured
                edges[tick].response = rtl_token(owner)
                captured = None
            elif operation == 'append':
                if owner not in slots:
                    if not free:
                        raise ValueError('restore owner cannot be allocated before this edge')
                    slots[owner] = heapq.heappop(free)
                append = (slots[owner], value, extra)
                if response is None:
                    edges[tick+period].appends.append(append)
                else:
                    if extra != response.pc & 1:
                        raise ValueError('staged append path bit differs from its captured PC')
                    response.query_owner = slots[owner]
                    edges[tick].response_bit = value
                    edges[tick].response_append = append
                    response = None
            elif operation == 'undo':
                edge = edges[tick+period]
                edge.undo += value
                edge.restore = slots[owner]
            elif operation == 'release':
                released.append(slots.pop(owner))
            elif operation == 'service_start':
                if value != tick+2*period:
                    raise ValueError('staged trace requires exactly two service cycles')
                service.update(range(tick, min(value, end)+1, period))
            elif operation == 'publish':
                publications.add(tick)
        for slot in released:
            heapq.heappush(free, slot)

    raw_ring = [0]*1024
    checkpoint = {}
    head = path = pending = 0
    empty = Edge()
    for tick in range(0, end+1, period):
        edge = edges.get(tick, empty)
        external_work = edge.undo or edge.appends
        if (edge.response and (external_work or edge.cancel or tick in publications)
                or external_work and tick in publications
                or edge.request and external_work and not edge.cancel
                or len(edge.appends)>3 or edge.undo>512):
            raise ValueError(f'staged history operands collide at edge {tick}')
        if edge.cancel:
            pending = 0
        elif edge.response:
            if edge.response != pending or edge.response_append is None:
                raise ValueError(f'no matching staged append at edge {tick}')
            pending = 0
        elif edge.request:
            if pending:
                raise ValueError(f'occupied staged request at edge {tick}')
            pending = edge.request
        if edge.undo:
            head = (head+edge.undo) % 1024
            path = checkpoint[edge.restore]
        appends = (edge.response_append,) if edge.response else edge.appends
        for slot, bit, path_bit in appends:
            checkpoint[slot] = path
            head = (head-1) % 1024
            raw_ring[head] = bit
            path = ((path<<1)|path_bit) & 0xffff
        bits = sum(x[1]<<i for i, x in enumerate(edge.appends))
        path_bits = sum(x[2]<<i for i, x in enumerate(edge.appends))
        owners = sum(x[0]<<(9*i) for i, x in enumerate(edge.appends))
        raw = sum(raw_ring[(head+age)%1024]<<age for age in range(130))
        yield (int(edge.cancel), edge.request, edge.pc, edge.query_owner,
               edge.response, edge.response_bit, edge.undo, edge.restore, len(edge.appends),
               bits, path_bits, owners, int(tick in service), int(tick in publications),
               pending, raw, path, head)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--period-ticks', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.trace.open(newline='') as stream, args.output.open('x') as output:
            for frame in replay(stream, args.period_ticks):
                output.write(' '.join(f'{value:x}' for value in frame)+'\n')
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
