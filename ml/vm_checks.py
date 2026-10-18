"""Go/no-go for the ML stack the models need, run inside IBM's s390x image on the VM (brief task 3).

Run: python ml/vm_checks.py   (in the Jupyter `notebook` container or `docker compose run app`)
"""
import io
import platform
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

CHECKS: list[tuple[str, Callable[[], str]]] = []


def check(name: str):
    def register(fn: Callable[[], str]) -> Callable[[], str]:
        CHECKS.append((name, fn))
        return fn
    return register


@check("platform")
def _platform():
    nnpa = "nnpa" in Path("/proc/cpuinfo").read_text().split()
    return f"{platform.machine()}, {sys.byteorder}-endian, NNPA flag {'present' if nnpa else 'MISSING'}"


@check("versions")
def _versions():
    return f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}, xgboost {xgb.__version__}"


def _json_round_trip(booster: xgb.Booster, dm: xgb.DMatrix) -> float:
    # JSON is the only format that is safe across endianness; a pickle written on x86 is garbage on s390x
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "m.json"
        booster.save_model(path)
        again = xgb.Booster(model_file=str(path))
    return float(np.max(np.abs(booster.predict(dm) - again.predict(dm))))


@check("xgboost survival:aft")
def _aft():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(2000, 4))
    hours = np.exp(1 + 0.5 * x[:, 0] + rng.normal(scale=0.5, size=2000))
    dm = xgb.DMatrix(x)
    dm.set_float_info("label_lower_bound", hours)
    dm.set_float_info("label_upper_bound", hours)
    booster = xgb.train({"objective": "survival:aft", "aft_loss_distribution": "normal",
                         "aft_loss_distribution_scale": 1.0, "tree_method": "hist", "max_depth": 3},
                        dm, num_boost_round=50)
    corr = np.corrcoef(np.log(booster.predict(dm)), x[:, 0])[0, 1]
    return f"trained, corr(pred, true driver) = {corr:.2f}, JSON round-trip max diff {_json_round_trip(booster, dm):.1e}"


@check("xgboost count:poisson")
def _poisson():
    rng = np.random.default_rng(1)
    x = rng.normal(size=(2000, 3))
    y = rng.poisson(np.exp(0.3 + 0.6 * x[:, 0]))
    dm = xgb.DMatrix(x, label=y)
    booster = xgb.train({"objective": "count:poisson", "tree_method": "hist", "max_depth": 3}, dm, num_boost_round=50)
    return f"trained, mean pred {booster.predict(dm).mean():.2f} vs mean y {y.mean():.2f}, JSON round-trip max diff {_json_round_trip(booster, dm):.1e}"


@check("tensorflow + zDNN plugin")
def _tf():
    import importlib.metadata
    import tensorflow as tf
    # the plugin adds no TF device: it swaps in NNPA kernels from this .so, so its presence is the check
    kernels = Path(tf.__file__).parent / "core" / "kernels" / "_z_ops.so"
    if not kernels.exists():
        raise FileNotFoundError(f"{kernels} missing, so NNPA kernels are not loaded")
    plugin = importlib.metadata.version("ibm-zdnn-plugin")
    devices = [d.device_type for d in tf.config.list_physical_devices()]
    model = tf.keras.Sequential([tf.keras.Input((4,)), tf.keras.layers.Dense(8, activation="relu"),
                                 tf.keras.layers.Dense(24, activation="softmax")])
    x = np.random.default_rng(2).normal(size=(64, 4)).astype("float32")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "m.keras"
        model.save(path)
        again = tf.keras.models.load_model(path)
    diff = float(np.max(np.abs(model.predict(x, verbose=0) - again.predict(x, verbose=0))))
    return f"tf {tf.__version__}, ibm-zdnn-plugin {plugin} kernels loaded, devices {devices}, .keras round-trip max diff {diff:.1e}"


@check("pandas on ENWL-shaped data")
def _pandas():
    raw = "incident_date_time;district_name;incident_duration\n2024-01-05 10:00:00;Bolton;95\n2024-01-05 23:10:00;Bolton;\n2024-01-06 01:00:00;Oldham;30\n"
    df = pd.read_csv(io.StringIO(raw), sep=";")
    df["incident_date_time"] = pd.to_datetime(df["incident_date_time"])
    daily = df.groupby([df["incident_date_time"].dt.date, "district_name"]).size()
    return f"read ; CSV, parsed dates, {len(daily)} district-days, missing durations kept as NaN ({df['incident_duration'].isna().sum()})"


def main() -> None:
    failed = []
    for name, fn in CHECKS:
        try:
            print(f"GO     {name}: {fn()}")
        except Exception as e:  # every failure is reported, so one broken library doesn't hide the others
            failed.append(name)
            print(f"NO-GO  {name}: {type(e).__name__}: {e}")
    print("\n" + ("ALL GO" if not failed else "NO-GO: " + ", ".join(failed)))


if __name__ == "__main__":
    main()
