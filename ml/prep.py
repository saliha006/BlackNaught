"""Harmonised ENWL and UKPN outage tables for the duration models (brief task 4).

Run on the VM: python -m ml.prep <raw-dir> <out-dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MIN_DURATION_MIN = 5   # brief: both sources cut at 5 minutes (UKPN's IIS records already start at 3)
FIRST_YEAR = 2000      # ENWL has 3 stray rows from 1997-98 before continuous records begin
TRAIN_LAST_YEAR, VALIDATE_YEAR = 2022, 2023
COLUMNS = ["source", "start", "duration_min", "customers", "voltage", "cause", "primary_substation", "district",
           "event_id", "split"]
# ENWL codes LV as text and HV/EHV as nominal kV
VOLTAGE = {"LV": "LV", "6.6": "HV", "11": "HV", "25": "EHV", "33": "EHV", "132": "EHV"}


def split_by_year(start: pd.Series, event_id: pd.Series) -> pd.Series:
    year = start.dt.year
    # a storm that crosses New Year stays in one split, so none of its outages leak into validation or test
    year = year.where(event_id.isna(), year.groupby(event_id).transform("min"))
    return pd.Series(np.select([year <= TRAIN_LAST_YEAR, year == VALIDATE_YEAR], ["train", "validate"], "test"),
                     index=start.index)


def load_enwl(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, sep=";", low_memory=False, dtype={"voltage": str, "primary_substation": str},
                      usecols=["incident_date_time", "incident_duration", "customer_affected", "voltage",
                               "direct_cause_category", "primary_substation", "district_name", "exceptional_event_id"])
    start = pd.to_datetime(raw["incident_date_time"], utc=True, format="ISO8601")
    table = pd.DataFrame({
        "source": "enwl",
        "start": start,
        "duration_min": raw["incident_duration"].astype(float),
        "customers": raw["customer_affected"],
        "voltage": raw["voltage"].str.strip().map(VOLTAGE),
        "cause": raw["direct_cause_category"],
        "primary_substation": raw["primary_substation"],
        "district": raw["district_name"].str.strip(),
        "event_id": raw["exceptional_event_id"],
        "split": split_by_year(start, raw["exceptional_event_id"]),
    })
    return table[COLUMNS]


def load_ukpn(path: Path) -> pd.DataFrame:
    """One row per incident from IIS restoration stages; the whole file is the cross-operator test."""
    raw = pd.read_csv(path, sep=";", low_memory=False,
                      usecols=["incident_reference", "start_date_time", "end_date_time", "customers_restored",
                               "reinteruption_stage"])
    raw["start"] = pd.to_datetime(raw["start_date_time"], utc=True, format="ISO8601")
    raw["end"] = pd.to_datetime(raw["end_date_time"], utc=True, format="ISO8601")
    # a re-interruption stage cuts customers already counted once: it adds time, not customers
    raw["first_cut"] = raw["customers_restored"].where(raw["reinteruption_stage"] != "Y", 0)
    incidents = raw.groupby("incident_reference").agg(start=("start", "min"), end=("end", "max"),
                                                      customers=("first_cut", "sum"))
    table = pd.DataFrame({
        "source": "ukpn",
        "start": incidents["start"],
        "duration_min": (incidents["end"] - incidents["start"]).dt.total_seconds() / 60,
        "customers": incidents["customers"],
        "split": "crosscheck",
    }).reset_index(drop=True)
    return table.reindex(columns=COLUMNS)


def harmonise(table: pd.DataFrame) -> pd.DataFrame:
    keep = (table["duration_min"] >= MIN_DURATION_MIN) & (table["start"].dt.year >= FIRST_YEAR)
    return table[keep].reset_index(drop=True)


def describe(name: str, raw: pd.DataFrame, kept: pd.DataFrame) -> str:
    hours = kept["duration_min"] / 60
    lines = [
        f"{name}: {len(raw):,} outages -> {len(kept):,} kept "
        f"({(raw['duration_min'] < MIN_DURATION_MIN).sum():,} under {MIN_DURATION_MIN} min, "
        f"{(raw['start'].dt.year < FIRST_YEAR).sum():,} before {FIRST_YEAR})",
        f"  splits: {kept['split'].value_counts().to_dict()}",
        f"  {kept['start'].min():%Y-%m-%d} .. {kept['start'].max():%Y-%m-%d}; median {hours.median():.2f} h, "
        f"over 24 h {(hours > 24).mean():.1%}, over 7 days {(hours > 168).mean():.2%}, longest {hours.max():,.0f} h",
        f"  customers median {kept['customers'].median():.0f}; voltage {kept['voltage'].fillna('unknown').value_counts().to_dict()}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raw_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, load, file in (("enwl", load_enwl, "enwl_unplanned-outages.csv"),
                             ("ukpn", load_ukpn, "ukpn_ukpn-iis.csv")):
        raw = load(raw_dir / file)
        kept = harmonise(raw)
        kept.to_csv(out_dir / f"{name}.csv.gz", index=False)
        print(describe(name, raw, kept), flush=True)
