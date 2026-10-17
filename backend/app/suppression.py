"""k≥11 small-cell suppression across the three nested grid levels (CMS cell-size rule, PRD §14).

Primary: any count of 1–10 is hidden (0 is published). Complementary: inside each parent, if the hidden
children could be recovered by subtraction (a single hidden child, or a hidden total under 11), the smallest
published sibling is hidden too, and if none is left the parent itself is hidden. Published counts from 20 up
are rounded to the nearest 5 so successive publishes can't be differenced exactly.
"""
from .cells import parent

K = 11
BAND_FROM = 20
BAND_STEP = 5


def _band(n: int) -> int:
    return n if n < BAND_FROM else BAND_STEP * round(n / BAND_STEP)


def counts_by_level(l1: dict[str, int]) -> dict[str, int]:
    counts = dict(l1)
    for cell, n in l1.items():
        up = parent(cell)
        counts[up] = counts.get(up, 0) + n
        top = parent(up)
        counts[top] = counts.get(top, 0) + n
    return counts


def publish(l1: dict[str, int]) -> dict[str, int | None]:
    """cell_id → published count, or None when suppressed."""
    counts = counts_by_level(l1)
    published: dict[str, int | None] = {c: None if 0 < n < K else n for c, n in counts.items()}
    for child_level in ("L1:", "L2:"):
        families: dict[str, list[str]] = {}
        for cell in counts:
            if cell.startswith(child_level):
                families.setdefault(parent(cell), []).append(cell)
        for up, kids in families.items():
            hidden = [k for k in kids if published[k] is None and counts[k] > 0]
            while hidden and (len(hidden) == 1 or sum(counts[k] for k in hidden) < K):
                visible = sorted((k for k in kids if published[k] is not None and counts[k] > 0), key=counts.get)
                if not visible:
                    published[up] = None
                    break
                published[visible[0]] = None
                hidden.append(visible[0])
    return {c: None if v is None else _band(v) for c, v in published.items()}
