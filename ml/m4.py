"""M4, GB grid stress from frequency (brief task 12, prediction layer 3): a rule, not a trained model.

The rule projects time to the grid's LFDD rung from the current rate of change of frequency and warns when that time
is shorter than the grid's horizon x fragility. It is replayed on NESO's 1-s data for 9 Aug 2019, the only LFDD event
in GB since 2008, against the live band rule (backend/app/stress.py), and run over the latest 12 months of 1-s data
to count false alarms. Every threshold is set here before the replay is scored.

Run on the VM: python -m ml.m4 <event-month.csv> <normal-month.csv>... > result.json
"""
import json
import sys
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

NORMAL_LOW = 49.8      # GB operational limit, as in backend/app/stress.py
STATUTORY_LOW = 49.5   # GB statutory limit
LFDD_HZ = 48.8         # low-frequency demand disconnection, stage 1 (NC ER annex, GB values)
ROCOF_WINDOW_S = 5     # NESO's 1-s values jitter by ~0.01 Hz; 5 s keeps the slope from chasing that noise
HORIZON_S = 60         # 9 Aug 2019 took ~1.5 min from 50 Hz to LFDD, so a minute is the most a rule could promise
FRAGILITY = 1.0        # GB is the reference grid; a weaker grid's YAML raises this to warn earlier
EPISODE_GAP_S = 60     # alerts closer than this are one incident to an operator, not two alarms


def load(path: Path) -> pd.Series:
    """Frequency on a 1-s grid; seconds NESO didn't publish stay NaN so no slope is taken across a gap."""
    raw = pd.read_csv(path)
    # 2019 files carry a +0100 offset; files from 2025 on are naive UTC
    t = pd.to_datetime(raw["dtm"], utc=True, format="mixed")
    f = pd.Series(raw["f"].to_numpy(dtype=float), index=t).sort_index()
    f = f[~f.index.duplicated()]
    return f.reindex(pd.date_range(f.index[0], f.index[-1], freq="1s"))


def signals(f: pd.Series) -> pd.DataFrame:
    rocof = (f - f.shift(ROCOF_WINDOW_S)) / ROCOF_WINDOW_S
    with np.errstate(divide="ignore", invalid="ignore"):
        t_to_lfdd = np.where(rocof < 0, (f - LFDD_HZ) / -rocof, np.inf)
    return pd.DataFrame({
        "band_stressed": f < NORMAL_LOW,
        "band_emergency": f < STATUTORY_LOW,
        "m4_warning": (f < NORMAL_LOW) & (t_to_lfdd < HORIZON_S * FRAGILITY),
    }, index=f.index)


def episodes(alert: pd.Series) -> int:
    times = alert.index[alert.to_numpy()]
    if len(times) == 0:
        return 0
    return 1 + int(((times[1:] - times[:-1]) > pd.Timedelta(seconds=EPISODE_GAP_S)).sum())


def lead_times(f: pd.Series, lookback_s: int = 600) -> dict:
    """Seconds between each signal's first alert and the first reading at or below LFDD, within the run-up."""
    below = f.index[(f <= LFDD_HZ).to_numpy()]
    if len(below) == 0:
        return {"lfdd_at": None}
    hit = below[0]
    window = signals(f)[hit - pd.Timedelta(seconds=lookback_s): hit]
    out = {"lfdd_at": hit.isoformat(), "min_hz": float(f[hit - pd.Timedelta(seconds=lookback_s):
                                                          hit + pd.Timedelta(seconds=lookback_s)].min())}
    for name in window:
        first = window.index[window[name].to_numpy()]
        out[name] = {"first_alert": first[0].isoformat(), "lead_s": int((hit - first[0]).total_seconds())} \
            if len(first) else None
    return out


def false_alarms(months: Iterable[pd.Series]) -> dict:
    """Every alert episode in months without an LFDD event counts as a false alarm."""
    counts, seconds_alerting = {}, {}
    n, lfdd_seconds, valid, low = 0, 0, 0, np.inf
    for f in months:   # one month (~2.6 M seconds) in memory at a time
        sig = signals(f)
        for name in sig:
            counts[name] = counts.get(name, 0) + episodes(sig[name])
            seconds_alerting[name] = seconds_alerting.get(name, 0) + int(sig[name].sum())
        n, lfdd_seconds, valid = n + 1, lfdd_seconds + int((f <= LFDD_HZ).sum()), valid + int(f.notna().sum())
        low = min(low, float(f.min()))
    return {"months": n, "valid_hours": round(valid / 3600, 1), "seconds_at_or_below_lfdd": lfdd_seconds,
            "min_hz": round(low, 3),
            **{name: {"episodes": counts[name], "per_month": round(counts[name] / n, 2),
                      "share_of_time": round(seconds_alerting[name] / valid, 6)} for name in counts}}


def run(event: Path, normal: list[Path]) -> dict:
    return {"rule": {"normal_low": NORMAL_LOW, "statutory_low": STATUTORY_LOW, "lfdd_hz": LFDD_HZ,
                     "rocof_window_s": ROCOF_WINDOW_S, "horizon_s": HORIZON_S, "fragility": FRAGILITY,
                     "episode_gap_s": EPISODE_GAP_S},
            "replay": {"file": event.name, **lead_times(load(event))},
            "normal": {"files": [p.name for p in normal], **false_alarms(load(p) for p in normal)}}


if __name__ == "__main__":
    print(json.dumps(run(Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]]), indent=1))
