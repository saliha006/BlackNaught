"""Builds the results notebook: the three prediction layers re-scored in Jupyter on the VM from their saved models.

Nothing is retrained; each cell loads an artifact from ~/shared/nate-runs/models and scores it on data it never saw.
Usage: python ml/make_results_notebook.py <out.ipynb>
"""
import json
import sys
from pathlib import Path



def code(src: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src}


def md(src: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": src}


cells = [
    md("# Blacknaught: predicting blackouts, three layers\n"
       "Every number below is recomputed **on this IBM LinuxONE z17 VM** from the models trained here, on data they "
       "never trained on. Nothing is retrained in this notebook.\n\n"
       "| Layer | Question | Horizon |\n|---|---|---|\n"
       "| 1. Area fault risk (M8) | Which areas will have faults tomorrow? | A day |\n"
       "| 2. Home sensors | Will this home lose power in the next 30 minutes? | Minutes |\n"
       "| 3. Grid stress (M4) | Is the whole grid about to shed demand? | Seconds |"),
    code("import platform, subprocess, sys\n"
         "print('machine:', platform.machine(), '| byte order:', sys.byteorder)\n"
         "print(subprocess.run(\"lscpu | grep -E 'Machine type|Hypervisor'\", shell=True, capture_output=True, text=True).stdout)\n"
         "print('NNPA facility:', 'yes' if 'nnpa' in open('/proc/cpuinfo').read().split() else 'no')"),
    code("sys.path.insert(0, '/home/ibm-user/shared/nate')\n"
         "from datetime import date, timedelta\n"
         "from pathlib import Path\n"
         "import numpy as np, pandas as pd, matplotlib.pyplot as plt\n"
         "from ml import m4, m8, home_sensor\n"
         "DATA, MODELS = Path('/home/ibm-user/shared/nate/data'), Path('/home/ibm-user/shared/nate-runs/models')\n"
         "print(sorted(p.name for p in MODELS.iterdir()))"),

    md("## Layer 1: tomorrow's fault risk per area (M8)\n"
       "XGBoost Poisson on Open-Meteo weather (gusts, rain, temperature, snow), on top of each area's usual rate for "
       "the month. Trained on Electricity North West faults 2010–22; scored here on **2024–26**. The baseline is that "
       "usual rate alone (climatology), which is what runs live today."),
    code("area = m8.load(MODELS / 'm8_weather_enwl_v1.json')\n"
         "counts, centres = m8.load_faults(DATA / 'enwl_unplanned-outages.csv')\n"
         "weather = m8.weather_history(centres, m8.FIRST_DAY, counts['day'].max().strftime('%Y-%m-%d'), DATA / 'weather')\n"
         "frame = counts.merge(weather, on=['district', 'day'])\n"
         "test = frame[frame['day'].dt.year > m8.VALIDATE_YEAR]\n"
         "pd.Series(m8.brier_skill(area, test), name='P(3+ faults), 2024-26').to_frame()"),
    code("storm = test[(test['district'] == 'Cumbria') & test['day'].between('2025-01-15', '2025-02-02')]\n"
         "fig, ax = plt.subplots(figsize=(10, 4))\n"
         "ax.bar(storm['day'], storm['faults'], color='#bbb', label='actual faults')\n"
         "ax.plot(storm['day'], area.expected(storm), 'o-', color='#c0392b', label='M8 expected (weather)')\n"
         "ax.plot(storm['day'], area.base(storm), '--', color='#2c3e50', label='climatology expected (live today)')\n"
         "ax.set_yscale('symlog'); ax.set_ylabel('faults per day'); ax.legend()\n"
         "ax.set_title('Storm Éowyn, Cumbria, 24 Jan 2025: M8 raised its forecast 3.5x, climatology stayed flat')\n"
         "import matplotlib.dates as mdates\n"
         "ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b')); ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))\n"
         "plt.show()\n"
         "storm.assign(m8=area.expected(storm).round(1), climatology=area.base(storm).round(1))"
         "[['day', 'faults', 'wind_gusts_10m_max', 'm8', 'climatology']].sort_values('faults').tail(3)"),
    code("tomorrow = date.today() + timedelta(days=1)\n"
         "try:\n"
         "    risk = pd.DataFrame(area.area_risk(tomorrow)).sort_values('p_ge_k')\n"
         "    ax = risk.plot.barh(x='district', y='p_ge_k', legend=False, color='#c0392b', figsize=(8, 3.5))\n"
         "    ax.set_xlim(0, 1); ax.set_xlabel('P(3 or more faults)')\n"
         "    ax.set_title(f'Tomorrow ({tomorrow}), from the live Open-Meteo forecast'); plt.show()\n"
         "except (OSError, ValueError) as e:   # the forecast is fetched live; the scored results above don't depend on it\n"
         "    print('live forecast unavailable:', e)"),

    md("## Layer 2: will this home lose power in the next 30 minutes?\n"
       "Real nLine GridWatch sensors in Accra, Ghana (CC BY-NC 4.0, GPS and IDs stripped). The model reads the home's "
       "own last hour (voltage, flicker, time of day). Trained on days 1–4, calibrated on day 5, scored here on "
       "**days 6–7**, with a 5-run bootstrap over whole sensors for the ± figures."),
    code("home = home_sensor.load(MODELS / 'home_sensor_accra_v1.json')\n"
         "probe = home_sensor.probe\n"
         "table = probe.features(probe.per_site_grid(probe.load(DATA / 'accra')))\n"
         "day = table['bin'].dt.normalize(); days = sorted(day.unique())\n"
         "held_out = table[day > days[4]]\n"
         "result = home_sensor.evaluate(home, held_out)\n"
         "print(f\"{held_out['site_id'].nunique()} sensors, {len(held_out):,} windows on {str(days[5])[:10]} and {str(days[-1])[:10]}\")\n"
         "pd.DataFrame(result).T"),
    code("flag, base = result['flag_precision'], result['base_rate']\n"
         "fig, ax = plt.subplots(figsize=(7, 3))\n"
         "ax.barh(['every window', 'flagged \"elevated\"\\n(top 1%)'], [base['value'], flag['value']],\n"
         "        xerr=[base['sd'], flag['sd']], color=['#bbb', '#c0392b'])\n"
         "ax.set_xlabel('share that lost power within 30 minutes')\n"
         "ax.set_title(f\"Flagged homes: {flag['value']:.1%} lose power, {flag['value'] / base['value']:.1f}x the base rate\")\n"
         "plt.show()"),

    md("## Layer 3: grid stress from frequency (M4)\n"
       "A rule, not a trained model. Thresholds were committed before this replay was scored: warn when frequency is "
       "below 49.8 Hz and, at the last 5 seconds' rate of fall, would reach **48.8 Hz** (automatic demand "
       "disconnection, LFDD) within 60 s. Replayed on NESO's 1-second data for **9 August 2019**, GB's only LFDD "
       "event since 2008, when about 1.1 million customers were cut off."),
    code("f = m4.load(DATA / 'neso' / 'f 2019 8.csv')\n"
         "lead = m4.lead_times(f)\n"
         "pd.DataFrame({k: v for k, v in lead.items() if isinstance(v, dict)}).T"),
    code("hit = pd.Timestamp(lead['lfdd_at']); warn = pd.Timestamp(lead['m4_warning']['first_alert'])\n"
         "view = f[hit - pd.Timedelta(minutes=2): hit + pd.Timedelta(minutes=2)].tz_convert('Europe/London')\n"
         "fig, ax = plt.subplots(figsize=(10, 4))\n"
         "ax.plot(view.index, view, color='#2c3e50', lw=1.5, label='GB frequency (NESO, 1 s)')\n"
         "for hz, name in ((49.8, 'normal band 49.8 Hz'), (49.5, 'statutory 49.5 Hz'), (48.8, 'LFDD 48.8 Hz')):\n"
         "    ax.axhline(hz, ls=':', color='#888'); ax.text(view.index[0], hz + 0.02, name, color='#555', fontsize=9)\n"
         "ax.axvspan(warn.tz_convert('Europe/London'), hit.tz_convert('Europe/London'), color='#c0392b', alpha=0.15,\n"
         "           label=f\"warning: {lead['m4_warning']['lead_s']} s before demand disconnection\")\n"
         "ax.set_ylabel('Hz'); ax.legend(loc='upper right'); ax.set_title('9 August 2019, GB frequency (BST)')\n"
         "plt.show()"),
    code("normal = sorted((DATA / 'neso').glob('fnew-*.csv'))\n"
         "alarms = m4.false_alarms(m4.load(p) for p in normal)\n"
         "print(f\"{alarms['months']} normal months ({normal[0].stem[5:]} to {normal[-1].stem[5:]}), \"\n"
         "      f\"{alarms['valid_hours']:,.0f} h, lowest reading {alarms['min_hz']} Hz, no LFDD\")\n"
         "pd.DataFrame({name: {'warning before LFDD (s)': lead[name]['lead_s'], 'false alarms a month': alarms[name]['per_month']}\n"
         "              for name in ('band_stressed', 'band_emergency', 'm4_warning')}).T"),
    md("**Honest reading.** M4 matches the live band rule's warning within 3 seconds, so the band rule stays live. "
       "The seconds exist only on 1-second data: the live Elexon feed is every 15 s and about 1.5 minutes late. "
       "Frequency is the same everywhere on the grid, so it says *that* the grid is in trouble, never *where*; "
       "layers 1 and 2 answer where."),
]

notebook = {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}}
Path(sys.argv[1]).write_text(json.dumps(notebook, indent=1))
print("written", sys.argv[1])
