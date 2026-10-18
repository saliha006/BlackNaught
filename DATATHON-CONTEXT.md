# IBM Z Datathon 2026: rules, judging and context
*Merged 2026-10-18 from the guidebook digest, the 16 Oct team brief, the 16 Oct session summary and the idea ranking. Where they disagreed, the newer IBM handoff (`DATATHON INFO/IBMZ_Datathon_ClaudeCode_Handoff/HANDOFF.md`) wins. Originals: `_archive/2026-10-18-pre-merge/`. Our project spec: `BLACKNAUGHT.md`.*

## 1. Event essentials
- **Organisers:** Shooting Stars Foundation (SSF) + IBM.
- **Submission:** on **Hack2Skill**, by the **registered team leader only**.
- **Team:** 4. Manchester hub (EMEA). Prize pool $50k+, judged **per hub** (top 3 per hub).
- **Track:** we're in **Theme 1, Real-Time AI for Critical Decisions** ("Detect. Decide. Respond."), with Theme 2 (AI Secured) built in.
- **Must show:** "Your solution must demonstrate **why IBM Z / LinuxONE is the right platform** for your idea."

| When (BST) | What |
|---|---|
| Sat 17 Oct, 09:00–17:00 | In person; then virtual |
| **Sun 18 Oct** | **Submit by 09:30**, hard stop 10:00. Sources disagree (10:00 / "by eleven" / 11:30), so we use the earliest |
| Sun ~11:30 | Closing ceremony |
| 28 Oct | Winners announced |
| 18 Nov | IBM Z Day (winners may present) |

## 2. Submission checklist
- **Title:** `[<Team Name>_IBM Z Datathon 2026 Project]`. ⚠ Still need the team name + Hack2Skill team number.
- **Video ≤ 3:00:** problem, data, solution, **how it uses IBM Z: show the LinuxONE instance, its IP and the model**. Everyone speaks; captions burned in. Recorded against `http://148.100.78.95:<port>` (judges match IPs).
- **Public GitHub repo** with commits from every member, and a README covering:
  - problem; data + licences; architecture;
  - how to run it on LinuxONE; results;
  - choices, failures and fixes;
  - **who did what**; next steps;
  - every open-source library.
- **Deck PDF** (no empty demo slide; include a "proof it runs on LinuxONE" slide).
- **Screenshots** of containerisation, security, scalability, compute, plus the **mandatory labs**: run `scripts/proof.sh`; the training notebook in Jupyter.
- **Open-source list.** Optional: a flowchart.
- **After submitting,** keep the VM and app running until 28 Oct (judges may ask for proof).

## 3. Rules that bite
- **All code written during the event** (planning and research beforehand are fine). Original work only: no ideas taken from other teams.
- **Labs:** both mandatory labs before building: (1) Predictive AI, hybrid multi-model; (2) Predictive AI + Generative AI. The setup-call slide said "01 *or* 02". Do both.
- **Marist Terms of Use:**
  - **§4** open source only (add a LICENSE);
  - **§5 no benchmarking or publishing benchmark results** (ask #helpdesk before showing NNPA on/off timing);
  - **§9 no personal, health or card data** on the VM (our patients are synthetic; Accra GPS/ids are stripped);
  - **§11–12** never share private keys or logins.

## 4. Judging
**4 criteria × 10 = 40 points** (half-points used). **IBM said technical design is "the primary" criterion.**

| Criterion | 9–10 looks like |
|---|---|
| Value + theme fit | Impactful solution to a *critical* need; seamless theme fit ("if you're saving lives you score a 10 in that column") |
| Novelty | Highly innovative, strong end-to-end. 0–3 = "commonly available" |
| Technical + LinuxONE + open-source AI/ML | *Optimises* LinuxONE; exceptional AI/ML on it; **fully exploits security and/or compute** |
| Execution + pitch | Professional team video, compelling demo, within time |

- **AI Innovation Excellence award** (+20): novelty + transformational impact.
- **Special awards:** Most Innovative AI Theme, Most Creative AI Solution, Highest Participation, **Best IBM Z Advocacy**.
- **What judges check:** network traffic, **IP addresses in videos**, installed packages, and that **every member contributed** (commits, video). AI-written code is fine.

**IBM's Submission Playbook** (setup call, slide 14):
- **Technical:** workloads **running live on L1CC** · **≥ 2 AI frameworks** · Docker/Podman · security **or** Telum.
- **Novelty:** 100% new code · don't lightly modify the labs · pair predictive models with Granite reasoning.
- **Pitch:** problem + **persona** + value · demo **recorded on LinuxONE** · each member's role.
- **Community:** a **quantified** beneficiary population · one explicit theme · ethical, transparent reasoning.

## 5. What wins (research §4–§6)
- **Past winners scored ≤ ~27/40** on the 2026 rubric, and **none above 7/10 on LinuxONE**: most ran on a laptop or Watson Studio. **Deep, proven LinuxONE use is the gap.**
- **Winning formula:**
  - a named person + a sourced harm in the first 15 s;
  - output is a **decision**, not a label;
  - one unusual ingredient;
  - an honest baseline;
  - one "wow" visual;
  - LinuxONE proven on screen;
  - a repo that matches the video.
- **No past winner had a closed loop.** Ours grades itself live against real restorations.
- **Anti-wrapper test:**
  1. delete the LLM and the decision still works;
  2. the value is our data, model and design;
  3. it beats "just ask ChatGPT";
  4. it can't be rebuilt in an afternoon;
  5. the LLM's job is small and checked;
  6. it runs on LinuxONE.
- **Video skeleton (aim 2:50):**
  1. 0:00 hook (person + stat);
  2. 0:15 data;
  3. 0:35 live demo with the wow moment;
  4. 1:35 IBM Z (diagram + terminal: s390x, `docker ps`, the model, security);
  5. 2:20 proof + one honest limitation;
  6. 2:40 close, with the team.

  Our own beat sheet is `BLACKNAUGHT.md` §17.

## 6. Platform in one paragraph (details: HANDOFF §2–§3, §9)
- **The VM:** `Datathon4Musketeers`, `148.100.78.95`, user `linux1`, key-only (individual keys). z17 (9175), **s390x big-endian, NNPA present**, 3 vCPU / 8 GB / 50 GB, Ubuntu 24.04, **no backups** (push to git).
- **Images:** IBM's `jupyterlab-image-s390x` (Python 3.12, TF + zDNN, torch + torch_nnpa, XGBoost, `llama_cpp_python` with zDNN) is the base for everything.
- **Never pip-install** numpy, pandas, TF or torch.
- **Avoid:** pyarrow/parquet/polars/DuckDB, psycopg2 wheels, `cryptography` (no s390x wheel), Ollama, external LLM APIs. GGUF files must be **-BE**.
- **Network:** only port 22 and Jupyter's 38888 are open (iptables); internal services bind to 127.0.0.1.

## 7. How we chose Blacknaught
- **The pick:** on 16–17 Oct the team scored a pool of ideas with two harsh judges, two red-team teardowns and a fact-checking pass. **"Dark Hours" ranked first** (31/40 + 15/20 AI award): lives at stake, real labels, and an agent graded on real outcomes live. It was renamed **Blacknaught**.
- **The pivot:** on 17 Oct the teammates added sensors, localisation, area risk, alerts and any-grid-by-config.
- **The headline:** on 18 Oct it became **"predict blackouts before they happen + protect the most vulnerable"**. Current state: `BLACKNAUGHT.md` → NOW.
- **The other ideas** (Confirmation of Purpose, Mast, Overflow Watch/Spillcast, Vanish, Memory Lane, Cable Watch, Clone Watch…) are archived in `_archive/2026-10-18-pre-merge/DATATHON INFO/` and the research ledger's archived §7–§8.

## 8. Support
- **Discord:** `#ibm-z-sme-helpdesk` (70–80 IBM SMEs) and the Manchester hub channel.
- **Email:** linux1@us.ibm.com (platform), stemprograms@sstarsfoundation.org (event).
- **VM unresponsive:** Stop, then Start, in the L1CC portal (Ahmed).
