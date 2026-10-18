"""NNPA on/off timing (brief task 18, Ahmed): the same model on the same VM, NNPA on vs NNPA_DEVICES=0.

Each mode runs in its own fresh process (a separate `docker run` of bn-app, IBM's TF + zDNN image), because the
zDNN plugin decides at TensorFlow start-up whether supported ops go to the NNPA. The inputs are synthetic but
fixed-seed and shaped from the model's own input, so both modes score exactly the same rows. Never compared
against x86: only NNPA against this same machine's CPU path.

On the VM host (stdlib only), from a folder holding this file:
    python3 nnpa_timing.py <model.keras> <out.csv>     # runs both modes, writes the CSV, prints a summary
Inside bn-app (what the driver runs; one mode per process, JSON on stdout):
    python nnpa_timing.py --measure /m/<model.keras>
"""
import csv
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

BATCHES = (1, 256, 4096, 65536)
RUNS = 15
SEED = 7
IMAGE = "bn-app:latest"
MODES = {"nnpa_on": {}, "nnpa_off": {"NNPA_DEVICES": "0"}}


def measure(model_path: str) -> dict:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import keras
    import numpy as np
    import tensorflow as tf

    model = keras.saving.load_model(model_path, compile=False)
    features = model.input_shape[-1]
    # model.predict is what the scorer would call, but it carries ~30 ms of per-call setup; the bare graph call
    # shows what the kernels themselves cost, which is where the NNPA can make a difference
    graph = tf.function(lambda x: model(x, training=False))
    rng = np.random.default_rng(SEED)
    rows = []
    for batch in BATCHES:
        x = rng.standard_normal((batch, features), dtype=np.float32)
        model.predict(x, batch_size=batch, verbose=0)  # warm-up: traces the graph and loads the kernels once
        graph(x).numpy()
        predict_s, graph_s = [], []
        for _ in range(RUNS):
            start = time.perf_counter()
            model.predict(x, batch_size=batch, verbose=0)
            predict_s.append(time.perf_counter() - start)
            start = time.perf_counter()
            graph(x).numpy()
            graph_s.append(time.perf_counter() - start)
        median = statistics.median(predict_s)
        rows.append({"batch": batch, "median_ms": round(median * 1000, 3), "rows_per_s": round(batch / median),
                     "graph_ms": round(statistics.median(graph_s) * 1000, 3)})
    return {"tf": tf.__version__, "machine": platform.machine(), "devices": [d.device_type for d in
            tf.config.list_physical_devices()], "nnpa_devices": os.environ.get("NNPA_DEVICES", "(unset)"),
            "params": model.count_params(), "features": features, "runs": RUNS, "rows": rows}


def run_mode(model: Path, env: dict[str, str]) -> dict:
    """One mode in a fresh container, so nothing the other mode loaded or traced carries over."""
    flags = [arg for k, v in env.items() for arg in ("-e", f"{k}={v}")]
    done = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "/opt/venv/bin/python", *flags,
         "-v", f"{Path(__file__).resolve().parent}:/w:ro", "-v", f"{model.parent}:/m:ro", IMAGE,
         "/w/nnpa_timing.py", "--measure", f"/m/{model.name}"],
        capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=900, check=True)
    return json.loads(done.stdout.strip().splitlines()[-1])


def main() -> None:
    if sys.argv[1:2] == ["--measure"]:
        print(json.dumps(measure(sys.argv[2])))
        return
    model, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    results = {mode: run_mode(model, env) for mode, env in MODES.items()}
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mode", "batch", "predict_median_ms", "predict_rows_per_s", "graph_median_ms", "tf", "machine",
                    "nnpa_devices", "runs"])
        for mode, r in results.items():
            for row in r["rows"]:
                w.writerow([mode, row["batch"], row["median_ms"], row["rows_per_s"], row["graph_ms"], r["tf"],
                            r["machine"], r["nnpa_devices"], r["runs"]])
    on, off = (results[m]["rows"] for m in MODES)
    for a, b in zip(on, off):
        print(f"batch {a['batch']:>6}: predict NNPA on {a['median_ms']:>8.3f} ms, off {b['median_ms']:>8.3f} ms"
              f" | graph on {a['graph_ms']:>8.3f} ms, off {b['graph_ms']:>8.3f} ms")
    print(json.dumps({m: {k: v for k, v in r.items() if k != "rows"} for m, r in results.items()}))


if __name__ == "__main__":
    main()
