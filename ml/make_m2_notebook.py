"""Builds the M2 training notebook that runs in Jupyter on the VM (the run itself is the evidence).

Usage: python ml/make_m2_notebook.py <out.ipynb>
"""
import json
import sys
from pathlib import Path


def code(src: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src}


def md(src: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": src}


cells = [
    md("# Blacknaught M2: how long will this power cut last?\n"
       "Trained **on this IBM LinuxONE z17 VM** from 306,251 real Electricity North West outages (CC BY 4.0), "
       "tested on ENWL 2024–26 and on 178,864 UK Power Networks outages the models never saw. Every model gives "
       "S(t) = P(power still off t hours after the fault started); triage compares it with each patient's backup."),
    code("import platform, subprocess, sys\n"
         "print('machine:', platform.machine(), '| byte order:', sys.byteorder)\n"
         "print(subprocess.run(\"lscpu | grep -E 'Machine type|Hypervisor'\", shell=True, capture_output=True, text=True).stdout)\n"
         "print('NNPA facility:', 'yes' if 'nnpa' in open('/proc/cpuinfo').read().split() else 'no')"),
    code("import os, time\n"
         "os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'\n"
         "sys.path.insert(0, '/home/ibm-user/shared/nate')\n"
         "from pathlib import Path\n"
         "import numpy as np, pandas as pd\n"
         "from ml import m2\n"
         "enwl, ukpn = m2.load(Path('/home/ibm-user/shared/nate/data/prepared'))\n"
         "train, valid, test = (enwl[enwl['split'] == s] for s in ('train', 'validate', 'test'))\n"
         "median = float(train['customers'].median())\n"
         "rng = np.random.default_rng(m2.SEED)\n"
         "print(f'train {len(train):,} (2000-22) | validate {len(valid):,} (2023) | test {len(test):,} (2024-26) | UKPN {len(ukpn):,}')\n"
         "print('features:', list(m2.features(train.head(), median).columns))"),
    md("## 1. M1 baselines\nKaplan–Meier (the live stand-in), Kaplan–Meier per cause (cause isn't known live, so this one "
       "is offline only), and a log-linear model on the live features."),
    code("baselines = []\n"
         "for build in (lambda: m2.Km(train['duration_h']), lambda: m2.KmByCause(train), lambda: m2.LogNormal(train, median)):\n"
         "    t0 = time.perf_counter(); model = build(); baselines.append(model)\n"
         "    print(f'{model.name}: trained in {time.perf_counter() - t0:.1f} s')"),
    md("## 2. M2 XGBoost AFT\nGradient-boosted accelerated-failure-time model. Voltage is hidden on a third of training "
       "rows so outages with no voltage (all of UKPN) get a trained answer."),
    code("t0 = time.perf_counter()\n"
         "aft = m2.Aft(train, valid, median, rng)\n"
         "print(f'trained in {time.perf_counter() - t0:.1f} s, best round {aft.booster.best_iteration}, spread sigma {aft.sigma:.3f}')"),
    md("## 3. M2 Keras discrete-time hazard MLP\n24 hourly bins plus one for longer outages. This is the network that "
       "IBM's zDNN plugin runs on the Telum NNPA."),
    code("t0 = time.perf_counter()\n"
         "mlp = m2.HazardMlp(train, valid, median, rng)\n"
         "print(f'trained in {time.perf_counter() - t0:.1f} s')"),
    md("## 4. Scores on outages none of the models trained on\nLower Brier and integrated Brier (IBS) are better; "
       "C-index 0.5 means no ranking skill. KM is the model triage uses today."),
    code("models = baselines + [aft, mlp]\n"
         "board = m2.scoreboard(models, {'ENWL 2024-26': test, 'UKPN cross-check': ukpn})\n"
         "km = board[board['model'] == 'M1 Kaplan-Meier'].set_index('test')['ibs_24h']\n"
         "board['ibs_skill_vs_km'] = (1 - board['ibs_24h'] / board['test'].map(km)).round(3)\n"
         "board"),
    code("out = Path('/home/ibm-user/shared/nate-runs/models'); out.mkdir(parents=True, exist_ok=True)\n"
         "aft.booster.save_model(out / 'm2_aft.json'); mlp.model.save(out / 'm2_hazard.keras')\n"
         "import json\n"
         "(out / 'm2_metrics.json').write_text(json.dumps({'customers_median': median, 'aft_sigma': aft.sigma,\n"
         "    'scores': board.to_dict(orient='records')}, indent=1))\n"
         "print(sorted(p.name for p in out.iterdir()))"),
]

notebook = {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}}
Path(sys.argv[1]).write_text(json.dumps(notebook, indent=1))
print("written", sys.argv[1])
