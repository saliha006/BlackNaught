from pathlib import Path

from ml import prep

ENWL_HEADER = ("incident_date_time;incident_duration;customer_affected;voltage;direct_cause_category;"
               "primary_substation;district_name;exceptional_event_id;total_customer_minutes_lost;restoration_date_time")
UKPN_HEADER = "incident_reference;start_date_time;end_date_time;customers_restored;reinteruption_stage;cause_code"


def enwl_row(start: str, minutes: int, voltage: str = "LV", event: str = "", district: str = "Bolton") -> str:
    return f"{start}T10:00:00+00:00;{minutes};10;{voltage};Companies;216144;{district};{event};999;2099-01-01T00:00:00+00:00"


def write(tmp_path: Path, name: str, header: str, rows: list[str]) -> Path:
    path = tmp_path / name
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


def test_enwl_keeps_only_whitelisted_columns_and_drops_short_and_early_outages(tmp_path):
    path = write(tmp_path, "enwl.csv", ENWL_HEADER, [
        enwl_row("2021-06-01", 120, "11", district="Bolton "),
        enwl_row("2021-06-02", 4),
        enwl_row("1998-01-01", 60),
    ])
    kept = prep.harmonise(prep.load_enwl(path))
    assert list(kept.columns) == prep.COLUMNS
    assert len(kept) == 1
    row = kept.iloc[0]
    assert (row["voltage"], row["district"], row["duration_min"], row["split"]) == ("HV", "Bolton", 120, "train")


def test_enwl_voltage_codes_map_to_classes(tmp_path):
    codes = ["LV", "6.6", "11", "33", "132", "99"]
    path = write(tmp_path, "enwl.csv", ENWL_HEADER, [enwl_row("2021-06-01", 60, code) for code in codes])
    assert prep.load_enwl(path)["voltage"].fillna("unknown").tolist() == ["LV", "HV", "HV", "EHV", "EHV", "unknown"]


def test_time_split_keeps_a_new_year_storm_in_one_split(tmp_path):
    path = write(tmp_path, "enwl.csv", ENWL_HEADER, [
        enwl_row("2022-12-31", 60, event="7"),
        enwl_row("2023-01-01", 60, event="7"),
        enwl_row("2023-03-01", 60),
        enwl_row("2024-05-01", 60),
    ])
    assert prep.load_enwl(path)["split"].tolist() == ["train", "train", "validate", "test"]


def test_ukpn_rolls_restoration_stages_into_incidents(tmp_path):
    path = write(tmp_path, "ukpn.csv", UKPN_HEADER, [
        "A;2023-06-01T10:00:00+00:00;2023-06-01T11:00:00+00:00;5;N;75",
        "A;2023-06-01T10:00:00+00:00;2023-06-01T13:00:00+00:00;3;N;75",
        "A;2023-06-01T12:00:00+00:00;2023-06-01T14:00:00+00:00;3;Y;75",
        "B;2023-06-02T09:00:00+00:00;2023-06-02T09:03:00+00:00;2;N;49",
    ])
    raw = prep.load_ukpn(path)
    kept = prep.harmonise(raw)
    assert len(raw) == 2 and len(kept) == 1
    row = kept.iloc[0]
    assert (row["duration_min"], row["customers"], row["split"]) == (240, 8, "crosscheck")
    assert kept["voltage"].isna().all() and list(kept.columns) == prep.COLUMNS


def test_describe_reports_what_was_dropped(tmp_path):
    path = write(tmp_path, "enwl.csv", ENWL_HEADER, [enwl_row("2021-06-01", 120), enwl_row("2021-06-02", 4)])
    raw = prep.load_enwl(path)
    text = prep.describe("enwl", raw, prep.harmonise(raw))
    assert "2 outages -> 1 kept (1 under 5 min, 0 before 2000)" in text
