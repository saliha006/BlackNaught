"""GB grid stress from frequency. Interim band rule from grids/gb.yaml values (PRD §5) until Nate's M4
(time-to-next-rung × fragility) replaces `state`."""

NORMAL = (49.8, 50.2)       # GB operational limits
STATUTORY = (49.5, 50.5)    # GB statutory limits
LFDD_HZ = 48.8              # automatic low-frequency demand disconnection starts


def state(hz: float | None) -> str:
    if hz is None:
        return "UNKNOWN"
    if NORMAL[0] <= hz <= NORMAL[1]:
        return "NORMAL"
    if STATUTORY[0] <= hz <= STATUTORY[1]:
        return "STRESSED"
    return "EMERGENCY"
