"""Conditional cluster placement and explicitly compressed detection-time stress."""
from collections import Counter
import math
from .models import HISTORY_WIDTHS, history_site
from .rng import rng


def translations(offsets, width=16, height=22, valid=346):
    """Whole-shape placements on a hypothetical tile; never clip a cluster."""
    return [(x, y) for y in range(height) for x in range(width)
            if all(0 <= x+dx < width and 0 <= y+dy < height and
                   (y+dy)*width+x+dx < valid for dx, dy in offsets)]


def cern_marks(rows, seed, mapping='contiguous'):
    """Sample K>=2 catalog entries uniformly; no measured P(MCU) is inferred.

    Coordinate offsets are placed on an ASSUMED 16x22 logical tile. Catalog
    selection and geometry share their source-specific namespaces across the
    mapping controls; dispersed placement uses its own namespace.
    """
    if mapping not in ('contiguous', 'interleaved', 'dispersed'):
        raise ValueError('unknown hypothetical mapping')
    catalog = [(row, translations(row['offsets_from_anchor'])) for row in rows
               if row['multiplicity_from_unique_coordinates'] >= 2]
    if not catalog or any(not places for _, places in catalog):
        raise ValueError('empty conditional catalog or a whole shape cannot fit')
    linear = [history_site(i) for i in range(346)]
    interleaved = ['W{}:{}'.format(word, bit) for bit in range(max(HISTORY_WIDTHS))
                   for word, width in enumerate(HISTORY_WIDTHS) if bit < width]
    marks, geometry, dispersed = (rng(seed, role) for role in ('catalog', 'geometry', 'dispersed'))
    while True:
        row, places = catalog[int(marks.integers(0, len(catalog)))]
        x, y = places[int(geometry.integers(0, len(places)))]
        cells = [(y+dy)*16+x+dx for dx, dy in row['offsets_from_anchor']]
        if mapping == 'dispersed':
            cells = list(dispersed.choice(346, size=len(cells), replace=False))
        order = interleaved if mapping == 'interleaved' else linear
        yield tuple(order[int(cell)] for cell in cells)


def flying_events(timestamps_ms, seed, horizon, duplicates='collapse', timing='observed', multiplicity='single'):
    """Return detection records mapped into a declared finite exposure horizon.

    Duplicated records are either retained as separate detections or collapsed
    per timestamp. They NEVER determine K. The optional CHARM K assumption is
    independent of Flying Laptop measurements. This mapping compresses time;
    it is not a physical per-second arrival model for the target CPU.
    """
    if duplicates not in ('collapse', 'preserve') or timing not in ('observed', 'permuted', 'fixed-count-poisson'):
        raise ValueError('unknown duplicate/timing policy')
    if multiplicity not in ('single', 'charm') or not isinstance(horizon, int) or horizon < 2:
        raise ValueError('invalid mark profile or exposure horizon')
    counts = Counter(timestamps_ms)
    if len(counts) < 2:
        raise ValueError('need at least two distinct detection times')
    sources = [(timestamp, group, occurrence) for group, timestamp in enumerate(sorted(counts))
               for occurrence in range(counts[timestamp] if duplicates == 'preserve' else 1)]
    times = [float(timestamp-sources[0][0]) for timestamp, _, _ in sources]
    span = times[-1]
    if not math.isfinite(span) or span <= 0:
        raise ValueError('invalid detection span')
    clock = rng(seed, 'time')
    if timing == 'permuted':
        gaps = clock.permutation([b-a for a, b in zip(times, times[1:])])
        times = [0.0]
        for gap in gaps:
            times.append(times[-1] + float(gap))
    elif timing == 'fixed-count-poisson':
        times = sorted(map(float, clock.uniform(0, span, len(sources))))
    records = []
    for time, (timestamp, group, occurrence) in zip(times, sources):
        mark, location = rng(seed, 'K', group, occurrence), rng(seed, 'location', group, occurrence)
        k = 1 if multiplicity == 'single' else (1 if int(mark.integers(0, 214)) < 205 else 2)
        # Original selected-word placement law: select a word by its bit width,
        # then a contiguous in-word run. This is a logical placement hypothesis.
        word_index = int(location.integers(0, 346))
        for word, width in enumerate(HISTORY_WIDTHS):
            if word_index < width:
                break
            word_index -= width
        start = int(location.integers(0, width-k+1))
        position = 1 + int(math.floor(time/span*(horizon-1)))
        records.append({'position': position, 'source_timestamp_ms': timestamp,
                        'source_group': group, 'record_in_group': occurrence,
                        'sites': tuple('W{}:{}'.format(word, start+b) for b in range(k))})
    return records
