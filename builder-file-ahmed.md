# Ahmed: Platform & Agent (LinuxONE VM, containers, security, sensor sim, agent loop, Granite, NNPA serving)
**GitHub:** `meep-boop` · **Branch:** `ahmed-platform` · **Brief last updated:** 2026-10-17 22:30 by Sali
**Spec:** `BLACKNAUGHT.md` (NOW at the top, then Part A spec, Part B backend design); the § numbers below refer to it. Platform facts: `DATATHON INFO/IBMZ_Datathon_ClaudeCode_Handoff/HANDOFF.md` (wins on platform).

## 0. How the agent reads this brief (every task)
0. **First, every prompt: `bash scripts/sync-context.sh`** (CLAUDE.md). If it says UPDATED, read `BLACKNAUGHT.md` → NOW and
   this brief again, and tell the user what changed before working.
1. Read the project `CLAUDE.md` in full, then this brief. Follow both.
2. **Only action `▶ Current tasks`**, top to bottom.
3. Before starting: `git fetch`, then read the new `progress.md` entries. Handle any open `⚠️ Conflicts: @ahmed` first.
4. **Ship sequence for each feature:**
   1. `no-slop`
   2. tests with coverage
   3. push `ahmed-platform`
   4. `git merge origin/main` into the branch and re-test
   5. merge to `main`
   6. add a `progress.md` entry
   - **Every completed task, not just features:** add a `progress.md` entry with your name, date and time, and push it
     to `main` straight away.
   - **Doc edits:** you may only move your own finished task into Archived. Publish it with
     `bash scripts/publish-context.sh "what changed"`. Never commit shared docs to `main`.

   Use the `debug` skill on every issue.

**Conflict tags:** `[⚠ conflicts with @name: what]` means the task touches someone else's area or a shared contract.

---

## 1. Ownership
**Owns:**
- **The LinuxONE VM** `Datathon4Musketeers`: access, keys, Docker, Jupyter, iptables, LUKS, and restarts from the portal. Only you can restart it, so stay reachable overnight.
- `/infra`:
  - `docker-compose.yml`: `app`, `postgres:17`, `edge` and `granite`, with `mem_limit` on each and restart policies;
  - the nginx edge on `debian:trixie` (OpenSSL 3.5, X25519MLKEM768);
  - the proof scripts and `evidence/`.
- **Signer:** ML-DSA-65 through an OpenSSL 3.5 subprocess (key mode 0400). It signs models, task lists and audit checkpoints, and publishes checkpoints off-box.
- **F2, the fuse-box sensor simulator, driven by real faults** (§6, §7).
- **F3, the evidence combiner and scale classifier.** Nate supplies the LR table.
- **F6, the agent loop** (§9): tools, guardrails, memory, decision log.
- **F8, Granite** through the lab image's `llama_cpp_python` (zDNN build).
- **NNPA serving** of Nate's Keras model, plus the scorer that refuses unsigned models.

**Does NOT touch:**

| Area | Owner |
|---|---|
| `/backend`, `/db` | @sali |
| `/ml`, `grids/*.yaml` | @nate |
| `/frontend` | @rama |

**Shared:** `docker-compose.yml`, `contracts/events.schema.json` (co-authored with Sali), `fixtures/*`.

## 2. VM access (no secrets in this file, ever)

| Item | Value |
|---|---|
| Host / user | `148.100.78.95` / `linux1` (key-only login; `sudo` works; root login disabled) |
| SSH alias (each person's own `~/.ssh/config`) | `Host datathon` · `HostName 148.100.78.95` · `User linux1` · `IdentityFile <your own private key>` · `ServerAliveInterval 30` |
| Jupyter | `http://148.100.78.95:38888` with a **custom** token (never the published default) |
| Portal | https://linuxone.cloud.marist.edu/#/login → Manage Instances (Stop, then Start, if SSH hangs) |

**Sali's public key** (add it to `~linux1/.ssh/authorized_keys`):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIP00BNV8Q3k7Yb2WJQEOZdUC49lkSYdngeg8c658F1Qp 006saliha@gmail.com
```

**Once Sali's key is added, Sali can:**
- `ssh datathon`
- run `git pull` and `docker compose` for backend services
- run backend tests on the VM
- run the DB migrations

**Only you do:**
- portal restarts
- credential rotation
- `authorized_keys` management
- LUKS setup
- the iptables policy
- the Jupyter token

## 3. Contract & Guardrails
**Scope contract.** Ahmed is building:
- A VM that runs everything in Compose on s390x within 8 GB.
- A **real agent**, with a tool list, guardrails and 3 logged decisions (§9). Its memory survives a restart.
- A sensor simulator that places fuse-box and anchor sensors on **real fault footprints**, with noise.
- Granite on the box.
- Signed models; a scorer that refuses tampered models; PQ TLS at the edge; a LUKS volume for Postgres.
- One uncut terminal "proof" take (§13).

**Out of scope:**
- mTLS, Kafka, mosquitto, LangGraph, k3s
- separate scheduler or ingest containers
- the ghcr llama.cpp images (CPU-only)
- real hardware sensors
- Secure Execution, HSM or Hyper Protect claims

**Guardrails:**
- **First task: rotate credentials.** The VM password and a Drive link to the private key were shared in a form. Nothing else starts until this is done.
- **Every member gets their own key.** Never pass the `.pem` around.
- **NNPA timing:** measure the same model on the same VM, with NNPA on vs `NNPA_DEVICES=0`, each in a fresh process. Save the result to `evidence/`. **Never compare against x86.** Ask #helpdesk whether the numbers can go in the video (ToU §5).
- **Never show the VM IP and a token in the same frame.**
- Escalations, CAP alerts and SMS to more than N people need **human approval**. An SMS reply can escalate but never de-escalate a no-backup patient.
- **Never pip-install** numpy, pandas, TF or torch. Base `app` on IBM's `jupyterlab-image-s390x`.
- Bind Postgres and Granite to `127.0.0.1`. Docker `-p` bypasses iptables.
- Load Granite in **one process only**. Stop the notebook kernels before demos.

---

## 4. ▶ Current tasks (2026-10-17 v3), in order
**Status update 2026-10-18 02:40 (from Sali)**
**🔄 Headline changed 2026-10-18 (ADR):** "Blacknaught **predicts blackouts before they happen** and **protects the people they'd hurt most**."
- **Prediction layers:**
  - area fault risk (hours to days);
  - home sensors (minutes): flags homes likely to lose power in 30 min; real Accra probe: 1 in 5 top alerts true, 9× chance;
  - grid stress (seconds, NESO).
- **Triage + alerting** of electricity-dependent people stay the core of "who this helps".
- **Never say:** "predicts every blackout", "minutes ahead from frequency", "voltage dips warn of blackouts" (the probe shows ≈ chance).
- **For you:** the Accra replay (F13) and the sensor simulator are now how layer 2 is shown live. Wire the replay so Nate's early-warning model scores it. The agent can then act early: pre-position a visit or SMS before the cut, for homes flagged at risk.
- **Start with `progress.md` → "Start here"** on GitHub (clone, hooks, `scripts/sync-context.sh`, VM access).
- ⚠ **Times in this brief (00:30 skeleton, 03:00 freeze) predate the team starting.** Sali will confirm a new freeze time on Discord; until then, prioritise top-down.
- **Already done on the VM by Sali:**
  - Docker 29.8 + Compose installed; Jupyter `notebook` on :38888 with a custom token (`~/.secrets/jupyter_token`); iptables persisted.
  - Probe captured in `evidence/01_platform.txt` (`scripts/proof.sh` re-runs it).
  - Sali's key added.
- **The backend stack is already running:** `bn-backend` = postgres:17 + app, from `backend/compose.backend.yml`.
  - Build edge, signer and granite **into that stack**, or `include:` it from `/infra`. **Don't start a second Postgres.** Agree the approach with Sali.
- **The backend is waiting on you for:**
  - the signer: `POST /sign`, `POST /verify`, then set `BN_SIGNER_URL`;
  - nginx `/api` + `/stream` (proxy_buffering off), so the demo has a public `https://148.100.78.95:8443`;
  - the agent calling `app.decisions.create()`;
  - the simulator publishing `contracts/events.schema.json` events.
- **Image fact:** the IBM image is RHEL 10.2 with OpenSSL **3.5.5** but **no `openssl` CLI**. So the trixie signer container is still the right home for ML-DSA.

1. 🟡 **🔒 Rotate the leaked credentials (FIRST).** *Partly done by Sali 2026-10-18 03:09: the leaked key was removed from `authorized_keys` (the old `.pem` is refused). **Still yours:** turn off the Drive link and change the portal password.*
   - Rotate the key pair in the portal if possible. At minimum, remove the leaked key from `authorized_keys`.
   - Delete the Drive link.
   - Check `last` and `journalctl -u ssh`.
   - Tell the organisers if the portal password was exposed.
   - Install gitleaks pre-commit.
2. ✅ **Team keys:** *Done 2026-10-18 03:09: individual keys for Sali, Ahmed, Nate and Rama; the shared key is retired.* Originally: ✅ Sali's key was added by Sali (23:25, using the team key). Still to do: Nate's and Rama's public keys, then **remove the leaked team key** once everyone has their own. Post "keys added" in `progress.md`. `[⚠ unblocks ALL]`
3. ✅ **Docker + Jupyter** (HANDOFF §3.1). *Done by Sali 2026-10-17 22:15.*
   - Install Docker and start the `notebook` container with a **custom token**.
   - `sudo iptables -I INPUT -p tcp --dport 38888 -j ACCEPT`.
   - Persist the iptables rules.
4. ✅ **Hour-1 probe** (HANDOFF §2.5). *Done by Sali: `evidence/01_platform.txt` (NNPA present, z17 9175).*
   - s390x, Big Endian, 9175, the `nnpa` flag, 3 vCPU, `free -h`, `openssl version` (trixie).
   - Post a NNPA go/no-go in `progress.md`. `[⚠ @nate needs the image]`
5. ⬜ **Labs 01 + 02 run and screenshotted** (they're mandatory). Split with the team if needed.
6. 🟡 **Contract freeze** (Sali drafted it; please ✅ in `progress.md` or add kinds): co-author `contracts/events.schema.json` with Sali. Events: heartbeat, last-gasp, DNO fault, frequency reading, SMS reply, IODA event, shedding stage. `[⚠ shared with ALL]`
7. 🟡 **Compose skeleton** (the backend stack already runs; extend it, see the status update)
   - `app` (FROM the IBM image + `pip install fastapi uvicorn pg8000 httpx`)
   - `postgres:17` on `127.0.0.1`
   - `edge` (nginx on trixie)
   - `granite`
   - `mem_limit` on each service, plus restart policies
   - *Done when:* `docker compose up -d` is green on the VM. `[⚠ @sali: app runs Sali's FastAPI; agree the entrypoint]`
8. ⬜ **LUKS2 volume for Postgres data** (HANDOFF §7.7, §9.5). Screenshot `cryptsetup luksDump`. `[⚠ @sali: DB data path]`
9. ⬜ **Signer**
   - ML-DSA-65 keygen; sign and verify (test `-rawin`).
   - Wrap the data key for the AES-GCM columns. `[⚠ @sali uses it for encrypted columns + audit checkpoints]`
10. ⬜ **🎯 Walking skeleton by 00:30** `[⚠ shared with ALL]`: ingest → DB → API → map, running on the VM.
11. ⬜ **F2: sensor simulator driven by real faults**
    - For each live or historic fault, put fuse-box sensors at synthetic enrolled homes in its affected unit postcodes (UKPN `fullpostcodedata`, NPg `postcode[]`). Add 2–3 anchor sensors per street, plus control sensors in neighbouring postcodes.
    - Affected sensors go silent at the real start and return at the real restoration. Heartbeat every 60 s; a last gasp on loss.
    - **Noise:** ~74% uptime, comms dropouts, some sensors behind backup, partial outages ("1 in 3 homes").
    - About 5k sensors is enough.
    - Writes go to Sali's events table, labelled SIMULATED.
    - `[⚠ @sali events table + geocoded faults; @nate household distributions]`
12. ⬜ **F3: evidence combiner + scale classifier** (§7)
    - The quorum rule.
    - Naive Bayes over sensors, DNO feeds, IODA and stress, using Nate's LR table.
    - A DNO fault declared in the postcode → P ≈ 1.0.
    - Stale source → LR = 1. Silence ≠ no outage.
    - Score: postcode precision/recall against the real DNO footprints → `evidence/localiser.json`.
13. ⬜ **NNPA serving.** Load Nate's **signed** `.keras` model and score every at-risk household × outage per tick as one batch via `model.predict` (graph mode). Refuse unsigned or tampered models. Run `ZDNN_ENABLE_PRECHECK=true` once and save the log. `[⚠ @nate hands over the model]`
14. ⬜ **F6: agent loop v1** (§9), a 60 s asyncio loop of perceive → assess → plan → act → observe → learn.
    - **Tools:** `notify_carer`, `assign_visit`, `request_supplier`, `escalate` (approval), `draft_cap_alert` (approval), `write_sitrep`, `field_briefing`, `mark_source_stale`, `recalibrate`.
    - **Capacity:** a greedy knapsack on harm-hours avoided (e.g. 5 workers and 12 patients; log who waits and why).
    - Every tool call is logged and signed. Memory in Postgres, with a restart test.
    - `[⚠ uses @nate's predict() + @sali's triage/decisions/grades tables]`
15. ⬜ **F8: Granite.** Granite 3.3 2B Instruct **BE** GGUF through the lab image's `llama_cpp_python` (server mode, threads 2, `max_tokens` ≤ 200, results cached).
    - Writes the field briefing, welfare-call script, situation report and CAP alert text.
    - A **number validator** rejects any number that isn't in the decision record.
    - Test: delete Granite, and the decisions stay the same.
16. ⬜ **Self-correction:** read the overnight grades; if Brier drifts, apply an isotonic correction per horizon (GB only) and log it before and after. `[⚠ @sali grades table]`
17. ⬜ **Edge PQ TLS.** nginx on OpenSSL 3.5; prove it with `openssl s_client -groups X25519MLKEM768`. Serves Rama's static build and proxies `/api` and `/stream` (SSE buffering off).
18. ⬜ **NNPA on/off timing → `evidence/nnpa_timing.csv`** (guardrail above), plus a Trivy scan of the app image and `iptables -L`.
19. ⬜ **Publish audit checkpoints off-box** (a git commit every N minutes). `[⚠ @sali audit chain]`
20. ⬜ **03:00 freeze.** Make sure the agent and grading are **running overnight**. Stay reachable for VM restarts.
21. ⬜ **06:00–07:00: record the uncut terminal take** (§13).
22. ⬜ **Video:** your line, plus the README section on the platform and proof.

## 5. Done log (newest first)
- (empty)

## 6. Waiting on / owed to others
- 📤 **Owed to ALL:** keys on the VM (first), the Compose skeleton by about 00:00.
- 📥 **Waiting on @nate:** the signed-model handover, the LR table, household distributions.
- 📥 **Waiting on @sali:** tables for events, decisions, grades and source health; geocoded faults.

## 7. Working-style notes for the agent
- Strongest on Linux. Explain IBM Z specifics (NNPA, CPACF, OpenSSL 3.5 PQC) precisely and never overclaim.
- Verbosity Level 0.

## 8. Reference
- **Image:** `registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest`
- **Granite BE:** `taronaeo/Granite-3.3-2B-Instruct-BE-GGUF` (Q4_K_M on CPU; Q8_0 for zDNN)
- **OpenSSL 3.5:** the `debian:trixie` container
- **s390x ✅:** postgres:17, nginx, debian:trixie, FastAPI, uvicorn, pg8000, httpx
- **s390x ❌:** LangGraph, psycopg2 wheel, TimescaleDB, PostGIS image, pyarrow, Ollama, ghcr llama.cpp (no zDNN)
- **Ledger:** `research-and-codebase.md` §12.1 (feeds, sensor-sim honesty rule)

---
── Archived (superseded 2026-10-17 — do NOT action) ──
- **The v2 task list (20 items):**
  - credential rotation, team access, probe, labs, contract freeze, Compose skeleton, signer
  - a generic 50–100k household simulator with London load shapes
  - NESO replay driver
  - walking skeleton by 18:00
  - agent v1, combiner, NNPA batch, self-correction, PQ edge, off-box checkpoints
  - optional ghcr llama.cpp Granite
  - 23:00 freeze, proof take, video
- **Why superseded:** PRD v3. The simulator now runs on real fault footprints. Granite moves to the lab image's `llama_cpp_python`. The agent gets explicit tools. LUKS added. Freeze moves to 03:00. The NESO replay driver moves to Nate's P1 F12, with Ahmed only on the replay hook.
