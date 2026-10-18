"""Builds notebooks/train_on_linuxone.ipynb: the training run judges can see in Jupyter on the VM."""
import json
from pathlib import Path


def code(src: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src}


def md(src: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": src}


cells = [
    md("# Blacknaught: training on IBM LinuxONE\n"
       "Fits the outage-duration model and the district fault-risk baseline **on this z17 VM**, from 312,936 real "
       "Electricity North West outages (CC BY 4.0) downloaded straight onto LinuxONE."),
    code("import platform, subprocess, sys\n"
         "print('machine:', platform.machine(), '| byte order:', sys.byteorder)\n"
         "print(subprocess.run(\"lscpu | grep -E 'Machine type|Model name'\", shell=True, capture_output=True, text=True).stdout)\n"
         "print('NNPA:', 'yes' if 'nnpa' in open('/proc/cpuinfo').read() else 'no')"),
    code("import sys, time\n"
         "sys.path.insert(0, '/home/ibm-user/shared/blacknaught/backend')\n"
         "from pathlib import Path\n"
         "from app import survival, arearisk\n"
         "DATA = Path('/home/ibm-user/shared/blacknaught/data/enwl_unplanned-outages.csv')\n"
         "print(DATA.name, round(DATA.stat().st_size / 1e6, 1), 'MB')"),
    md("## 1. Outage-duration model (Kaplan–Meier fallback until M2)"),
    code("t0 = time.perf_counter()\n"
         "km_doc = survival.fit_from_enwl(DATA)\n"
         "print(f\"fitted on {km_doc['n']:,} outages in {time.perf_counter() - t0:.1f} s on {platform.machine()}\")\n"
         "model = survival.KmModel(km_doc['curve'], km_doc['model_id'], 'notebook')\n"
         "for elapsed in (0, 1, 4, 12):\n"
         "    p = model.predict(elapsed)\n"
         "    print(f'outage already {elapsed:>2} h old → remaining q50 {p[\"quantiles\"][\"q50\"]:6.2f} h, '\n"
         "          f'q90 {p[\"quantiles\"][\"q90\"]:7.2f} h, P(still off in 4 h) {p[\"surv\"][3]:.2f}')"),
    md("## 2. District fault-risk baseline (climatology until M8)"),
    code("t0 = time.perf_counter()\n"
         "clim = arearisk.fit(DATA)\n"
         "print(f\"{len(clim['rates'])} districts, {clim['years']}, fitted in {time.perf_counter() - t0:.1f} s\")\n"
         "from datetime import date\n"
         "for r in arearisk.area_risk(clim, date(2026, 10, 19))[:6]:\n"
         "    print(f\"{r['district']:<12} expected {r['expected']:.2f} faults/day   P(≥3) {r['p_ge_k']:.2f}\")"),
    md("## 3. Two houses, one real fault\nSame outage, different answers: who runs out of backup first."),
    code("from app import harm\n"
         "pred = model.predict(1.0)\n"
         "for name, reserve in (('House A: oxygen, cylinder 3 h left', 3.0), ('House B: ventilator, 14 h battery', 14.0)):\n"
         "    a = harm.assess(pred['quantiles'], pred['surv'], reserve, 5, False)\n"
         "    print(f\"{name:<38} → {'ESCALATE' if a.escalate else 'SMS check'} | {'; '.join(a.why)}\")"),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
Path(__file__).with_name("train_on_linuxone.ipynb").write_text(json.dumps(nb, indent=1))
print("written")
