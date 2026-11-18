"""Convert a clean native history capture into cycle-exact RTL replay vectors."""
import argparse
import csv
import heapq
from itertools import groupby
from pathlib import Path

from .history_activity import check_trace


def replay(stream, period):
    summary = check_trace(stream)
    conflicts = set(summary['conflicting_operations']) - {'publication_shares_edge_with_work'}
    if conflicts or period < 2 or summary['capture_end_tick_exclusive'] % period:
        raise ValueError('trace requires scheduling or does not end on the chosen clock grid')
    stream.seek(0)
    stream.readline()
    rows = csv.DictReader(stream)
    # CPU operations at tick T drive the interval ending at T + period.
    # An autonomous publication is evaluated at its recorded opening edge T.
    port_rows = {}
    slots, slot_path = {}, {}
    free = list(range(512))
    raw_ring = [0]*1024
    head = path = 0
    service = set()
    publications = set()
    end = summary['capture_end_tick_exclusive']
    for tick, group in groupby(rows, key=lambda row: int(row['tick'])):
        if tick % period:
            raise ValueError(f'operation tick {tick} is off the clock grid')
        count = undo = restore = bits = path_bits = append_slots = pcs = prefixes = queries = 0
        freed_on_edge = []
        for row in group:
            op = row['operation']
            owner, value, auxiliary = (int(row[k]) for k in ('owner','value','auxiliary'))
            if op == 'undo':
                undo += value
                restore = slots[owner]
                head = (head + value) % 1024
                path = slot_path[owner]
            elif op == 'release':
                freed_on_edge.append(slots.pop(owner))
                del slot_path[owner]
            elif op == 'append':
                if owner not in slots:
                    if not free:
                        raise ValueError(f'owner allocation requires reuse within edge at {tick}')
                    slots[owner] = heapq.heappop(free)
                slot_path[owner] = path
                append_slots |= slots[owner] << (9*count)
                bits |= value << count
                path_bits |= auxiliary << count
                count += 1
                head = (head-1) % 1024
                raw_ring[head] = value
                path = ((path << 1) | auxiliary) & 0xffff
            elif op == 'query':
                pcs |= (value & 0xffffffff) << (32*queries)
                prefixes |= count << (2*queries)
                queries += 1
            elif op == 'service_start':
                if value != tick+2*period:
                    raise ValueError('trace service must be exactly two cycles')
                service.update(range(tick, min(value+period, end+period), period))
            elif op == 'publish':
                publications.add(tick)
        # A slot's write enable and restore address remain stable for
        # the whole cycle. Publish releases to the allocator afterwards.
        for slot in freed_on_edge:
            heapq.heappush(free, slot)
        raw = sum(raw_ring[(head+age)%1024] << age for age in range(130))
        port_rows[tick+period] = (undo, restore, count, bits, path_bits, append_slots,
                                 pcs, prefixes, raw, path, head)

    current = (0, 0, 0)
    for edge in range(0, end+1, period):
        frame = port_rows.get(edge, (0,)*8+current)
        if edge in publications and (frame[0] or frame[2]):
            raise ValueError(f'publication and data write share an active edge at {edge}')
        current = frame[-3:]
        yield (*frame[:8], int(edge in service), int(edge in publications), *current)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--period-ticks', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.trace.open(newline='') as stream, args.output.open('x') as out:
            for frame in replay(stream, args.period_ticks):
                out.write(' '.join(f'{v:x}' for v in frame)+'\n')
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
