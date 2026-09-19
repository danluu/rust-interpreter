"""Conservative within-span liveness over a previously qualified decoder."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/scalar-word-census'))
import words

ALL = (1 << 34) - 1


def direct_target(word, pc):
    """Recognize only target encodings; no branch feasibility assumptions."""
    if word & 0x7c000000 == 0x14000000:  # B or BL
        bits, shift = 26, 0
    elif word & 0xff000010 == 0x54000000:  # B.cond
        bits, shift = 19, 5
    elif word & 0x7e000000 == 0x34000000:  # CBZ/CBNZ, W or X
        bits, shift = 19, 5
    elif word & 0x7e000000 == 0x36000000:  # TBZ/TBNZ
        bits, shift = 14, 5
    else:
        return None
    delta = (word >> shift) & ((1 << bits) - 1)
    if delta & (1 << (bits - 1)):
        delta -= 1 << bits
    return pc + delta


def dead_definitions(operations, boundaries=()):
    """None means unknown/control transfer: everything can be observed there."""
    cuts = set(boundaries)
    live = ALL
    dead = set()
    for pc in range(len(operations) - 1, -1, -1):
        if pc + 1 in cuts:
            live = ALL
        op = operations[pc]
        if op is None:
            live = ALL
        elif op.pure and op.writes and not op.writes & live:
            dead.add(pc)
        else:
            live = op.reads | (live & ~op.writes)
    return dead


def analyze_span(code, start, end, incoming):
    assert 0 <= start < end <= len(code)
    if end - start > words.MAX_WORDS:
        return dict(declined=True, dead=[], unknown=end-start, kinds={})
    decoded = []
    unknown = 0
    for pc in range(start, end):
        try:
            # One synthetic end word permits decoding the last fallthrough;
            # the algorithm below independently makes every span exit live.
            op = words.decode(code[pc], pc, len(code) + 1)
        except AssertionError:
            op = None
            unknown += 1
        if op is not None and op.kind in ['branch', 'condition', 'return']:
            op = None
        decoded.append(op)
    dead = dead_definitions(decoded, (pc-start for pc in range(start+1,end) if pc in incoming))
    return dict(declined=False, dead=[start+pc for pc in sorted(dead)], unknown=unknown,
                kinds=dict(words.Counter(decoded[pc].kind for pc in dead)))
