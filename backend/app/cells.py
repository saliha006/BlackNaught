"""Fixed WGS84 grid, owned by the server. Integer micro-degrees avoid float drift at boundaries.

L1 0.010° lat × 0.016° lon (~1.1 km in N England); L2 = 5×5 L1; L3 = 5×5 L2.
"""
import math

L1_LAT_UDEG = 10_000
L1_LON_UDEG = 16_000
CHILDREN_PER_SIDE = 5


def _step(level: int) -> tuple[int, int]:
    factor = CHILDREN_PER_SIDE ** (level - 1)
    return L1_LAT_UDEG * factor, L1_LON_UDEG * factor


def cell_id(lat: float, lon: float, level: int = 1) -> str:
    lat_step, lon_step = _step(level)
    i = math.floor(round(lat * 1_000_000) / lat_step)
    j = math.floor(round(lon * 1_000_000) / lon_step)
    return f"L{level}:{i}:{j}"


def parent(cell: str) -> str:
    level, i, j = cell[1:].split(":")
    return f"L{int(level) + 1}:{int(i) // CHILDREN_PER_SIDE}:{int(j) // CHILDREN_PER_SIDE}"


def bounds(cell: str) -> list[tuple[float, float]]:
    """Closed ring of (lat, lon) corners."""
    level, i, j = (int(x) for x in cell[1:].split(":"))
    lat_step, lon_step = _step(level)
    s, w = i * lat_step / 1e6, j * lon_step / 1e6
    n, e = (i + 1) * lat_step / 1e6, (j + 1) * lon_step / 1e6
    return [(s, w), (n, w), (n, e), (s, e), (s, w)]
