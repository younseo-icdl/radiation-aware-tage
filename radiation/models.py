"""Source-informed logical upset schedules, independent of a predictor instance."""
import math
from .rng import rng

# Pinned plain-TAGE geometry: seven index/tag/tag folds, raw130, path16.
HISTORY_WIDTHS = (9, 9, 8, 9, 9, 8, 9, 10, 9, 9, 10, 9,
                  9, 11, 10, 9, 11, 10, 9, 12, 11, 130, 16)


def history_site(index):
    """Map a uniform S*=346 index to an explicit logical word:bit."""
    if not 0 <= index < sum(HISTORY_WIDTHS):
        raise ValueError('S* index outside the selected history')
    for word, width in enumerate(HISTORY_WIDTHS):
        if index < width:
            return 'W{}:{}'.format(word, index)
        index -= width


def events(seed, horizon, rate=None, scope='raw', single=False,
           multiplicity='charm', max_events=1000000):
    """Yield integer exposure positions and atomic logical XOR sites.

    Exposure positions are 1..horizon, inclusive. Poisson continuous arrivals
    are rounded UP to the next exposure position; collisions remain separate
    events. Rate is events per exposure unit, never flips per bit. A single
    event is uniform in exposure and independent of a Poisson rate.
    """
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError('horizon must be a positive integer')
    if scope not in ('raw', 'sstar') or multiplicity not in ('single', 'charm'):
        raise ValueError('unknown scope or multiplicity profile')
    if scope == 'sstar' and multiplicity != 'single':
        raise ValueError('S* sensitivity uses a single uniform selected bit')
    if max_events <= 0:
        raise ValueError('max_events must be positive')
    if single:
        if rate is not None:
            raise ValueError('single-event sensitivity has no event rate')
    elif rate is None or not math.isfinite(rate) or rate < 0:
        raise ValueError('Poisson rate must be finite and nonnegative')
    time_rng, k_rng, location_rng = (rng(seed, r) for r in ('time', 'K', 'location'))
    time, count = 0.0, 0
    while True:
        if single:
            position = int(time_rng.integers(1, horizon + 1))
        else:
            if rate == 0:
                return
            time += float(time_rng.exponential(1.0 / rate))
            if time > horizon:
                return
            position = max(1, int(math.ceil(time)))
        if count >= max_events:
            raise ValueError('event limit exceeded; shorten exposure or raise --max-events')
        if scope == 'raw':
            k = 1 if multiplicity == 'single' else (2 if k_rng.random() < 9 / 214 else 1)
            start = int(location_rng.integers(0, 130 - k + 1))
            sites = tuple('R{}'.format(start + offset) for offset in range(k))
        else:
            sites = (history_site(int(location_rng.integers(0, 346))),)
        yield position, sites
        count += 1
        if single:
            return
