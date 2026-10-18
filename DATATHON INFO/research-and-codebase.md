# Research & Codebase: IBM Z Datathon 2026 (team research master file)
One research file for this project (CLAUDE.md §10). Every source has a verdict: **KEEP** (≥2 independent sources) · **WEAK** (thin; not a sole basis) · **DO NOT USE** (refuted; quarantined at the bottom of its section).
Compiled 2026-10-16, the night before kick-off, from nine passes. Known gap across all passes: Reddit and most HN threads were unreachable or nonexistent for this event, so community consensus leans on HN, judge/winner blogs, ombudsman decisions and the IBM Community.

**Corrections applied:** IBM HElayers has **no s390x wheel** (PyPI, 2026-10-16). The claim in §3 is quarantined. Use Paillier (`phe`) instead.

## CATEGORY INDEX
| § | Covers | Use it for |
|---|---|---|
| §1 Platform | LinuxONE Community Cloud VM, the labs, team VM sharing, what runs on s390x, ToU limits | Setup, the VM-sharing answer, platform screenshots |
| §2 Past winners | Every findable IBM Z Datathon winner 2021–2025, with trends | What judges rewarded |
| §3 Theme research | 2025–26 methods per theme + s390x feasibility | Model choices |
| §4 Winning criteria | What wins and loses, anti-wrapper test, originality checklist, video template, 25h plan | Pitch and video |
| §5 Judge: prosecutor | Past winners scored harshly against the 2026 rubric | Failure patterns to avoid |
| §6 Judge: advocate | Winning formula + white space | What to copy (patterns, not ideas) |
| §7 Critic: originality | *Archived 2026-10-18* (other ideas, not Blacknaught) | `_archive/2026-10-18-pre-merge/research-section7-8-other-ideas.md` |
| §8 Critic: feasibility | *Archived 2026-10-18* (other ideas, not Blacknaught) | `_archive/2026-10-18-pre-merge/research-section7-8-other-ideas.md` |
| §11 Pivot critique (2026-10-17) | UK fault-data + LinuxONE pivot: what NESO can/can't do, fault-dataset comparison, transfer honesty, household view, overclaims, NNPA | Deciding the pivot; judge Q&A |
| §12 Realisation pass (2026-10-17) | Making pivot features real: live DNO localisation, real-fault sensor sim, Accra GridWatch real voltage, weather fault risk, household view, waveform sets, "±1 Hz = blackout" test | Feature scope for the last 16 h; judge Q&A on frequency |
| §13 Country + dataset pass (2026-10-17) | Free-healthcare outage grids: Ghana / Sri Lanka / South Africa scored against BD/PK; per-grid YAML constants; Eskom, nLine, PUCSL, Kaggle provenance checks; IODA signal for Sri Lanka 2025 | Picking the 2–3 target grids; `grid.yaml` values; judge Q&A on "why these countries" |
| Backend system-design pass (2026-10-17) | s390x package/image checks (pydantic-core, cryptography, pg8000, sse-starlette, llama_cpp server extras, postgres/nginx/trixie), nginx SSE, LUKS loop, CAP 1.2, pg8000 threading, audit triggers, session auth, cell suppression, censored grading, live-feed field checks | Backend build decisions; full rationale in `../system-design-choices.md` |
| Home-sensor precursor probe (2026-10-18) | Can a fuse-box/meter sensor predict its own power cut? Real Accra GridWatch week on the VM: modest early warning (ROC AUC 0.67, top-1% alerts 9× chance); low voltage alone ≈ chance | **Pitch wording for layer 2** ("flags homes most likely to lose power", not "predicts") |

---



---

<!-- §1: _ledgers/platform.md -->

# § LinuxONE platform + team workflow
Research pass: 2026-10-16, the night before the Datathon. Every source below was fetched in this pass.
Verdicts: **KEEP** (corroborated) · **WEAK** (thin or inferred) · **DO NOT USE** (refuted).
Rule: anything marked "verify on VM" gets checked with a one-line command on Oct 17 before we claim it in the video.

---

## Q1. LinuxONE Community Cloud (L1CC): what we actually get

**Registration and VM creation (KEEP)**
1. Register at `linuxone.cloud.marist.edu/#/register?flag=VM`. Put event code **SSF2026** in the project description. The jupyter-lab-ml README says this code gets "an instance with sufficient resources for ML notebooks".
2. Activate the account from the email (FAQ: "can't access VM" usually means not activated).
3. Portal → username menu → **Manage SSH Key Pairs**. Import your own public key, or generate one there. A generated `.pem` downloads **once** and cannot be retrieved again.
4. Manage Instances → Create → "General purpose VM" → name (no spaces) → image **`Ubuntu 24.04-Datathon`** or **`RHEL9.8-Datathon`** → the **single flavor** offered → choose the key → Create. Status goes NETWORKING → SPAWNING → **ACTIVE**. Note the IP.
5. `ssh -i key.pem linux1@<IP>`. User `linux1` with sudo. **Root login disabled. Key-only auth, no passwords.** These are fixed settings.

**Networking (KEEP):** each VM has a reachable IP. **Only SSH (22) is open by default.** The firewall is plain iptables. To open a port: `sudo iptables -I INPUT -p tcp --dport <port> -j ACCEPT`. To persist it on Ubuntu: `/etc/iptables/rules.v4`; on RHEL: `/etc/sysconfig/iptables.save`.

**Duration and data (KEEP):** access lasts up to **120 days**. Servers are **deleted on expiry and can't be restored**. There are **no backups** (ToU §6, §7). Expiry doesn't matter for a 25-hour event. Losing data does matter, so push to GitHub often.

**VM size (WEAK, verify on VM):** no current official vCPU/RAM/disk figure exists anywhere public. The last published spec was **2 vCPU / 4 GB / 50 GB** (an old Japanese deck covering RHEL 7.6). The SSF2026 flavor is described only as "sufficient for ML notebooks".
- Run `nproc; free -h; df -h /; lscpu | head -20` on day one and record the result.
- HN users describe the VM as feeling like "a fast two-core machine" with very fast single-thread speed and I/O.
- Hypervisor is **z/VM** (HN 2026 comment, Marist 2017 deck). The hardware generation isn't publicly stated. The jupyter-lab-ml README and the lab notebook both refer to **z17 / Telum II**.

**Hardware generation: z17/Telum II (WEAK, verify on VM).** Check `grep -o nnpa /proc/cpuinfo` and `lscpu`.
- The machine-type line in `/proc/cpuinfo` identifies the generation. 9175 = z17/LinuxONE 5, 3931 = z16.
- If `nnpa` appears in features, the AI accelerator is exposed to our guest. z/VM APAR VM66532 enables guest NNPA on z16.

**The labs: what the repo contains (KEEP)**
Repo: `github.com/linuxone-community-cloud/jupyter-lab-ml`. It ships one container, `registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest`.
- Run with `--network host`. JupyterLab listens on **:38888**. Default token is **`Your_Token1`** (the guidebook says `Your_Token`).
- Install: Docker on Ubuntu via `get.docker.com`, Podman on RHEL (`README_RHEL.md`).
- `~/shared` on the host mounts as `shared/` inside Jupyter.
- Upload limit is 200 MB per file. Install extra packages with `!{sys.executable} -m pip install …`.

| # | Notebook | What it does | Data | Stack |
|---|---|---|---|---|
| 1 | `Fraud_LSTM_Keras_TF.ipynb` | Card-fraud detection: 2×LSTM(200), 7-transaction window, 5 epochs × 500 steps, batch 16. Has an **ibm-zdnn-plugin / NNPA section** and a benchmark cell (median of 10 runs, batch 2000). | `transactions_history.csv` (IBM's Kaggle card-txn set) | Keras/TF 2.18 + ibm-zdnn-plugin |
| 2 | `Churn_Scikit_PyTorch.ipynb` | Client churn | customers 6,001 rows + transactions 20,000 rows | scikit-learn RandomForest → **PMML** export |
| 3 | `Digit_Class_TensorFlow.ipynb` | MNIST | MNIST | TF → **ONNX** export |
| 4 | `Loan_Approval_Demo.ipynb` | **Hybrid AI** loan decision: **XGBoost** risk score + **BM25 RAG** over policy PDFs + **IBM Granite via llama.cpp** writes the recommendation. Its llama.cpp build notes cover `-DGGML_ZDNN=ON` (NNPA) + OpenBLAS (VXE). | `sample_loan.csv`, pay-stub, W-2 and bank PDFs, policy folder | xgboost, llama_cpp_python, pypdf, rank-bm25 |

**Mapping to the two mandatory labs**
- **"Predictive AI + Generative AI" = `Loan_Approval_Demo.ipynb`.** Rated **KEEP**: the README literally calls it the "predictive and generative AI notebook".
- **"Predictive AI Hybrid AI scenarios (multi-model)" is less certain (WEAK).** No repo file uses "multi-model". Two candidates:
  - Notebooks 1–3: several predictive models plus the PMML and ONNX exports.
  - A separate IBM lab handed out on the day. IBM uses "multi-model" for "predictive + LLM together" (SHARE 2026 BYOD lab, Spyre marketing).
  - **Confirm in today's setup session recording or on Discord `#ibm-z-sme-helpdesk`.** Until then, run all 4 notebooks.

**Time estimates (my estimate, no official figure):**
- Docker install + image pull: ~15–30 min.
- Fraud LSTM: ~10–30 min. 2,500 training steps on a few vCPUs.
- Churn / MNIST: ~5–10 min each.
- Loan demo: ~5–15 min. The Granite load + generation is the slow part.
- Budget **~1.5–2 h for both labs, split across people.** Start the image pull the moment the VM is ACTIVE.

---

## Q2. Team sharing: one VM, four people

**Hard facts (KEEP)**
- Access is SSH-key-only, as user `linux1`. `~/.ssh/authorized_keys` is standard OpenSSH, so the owner can add any number of public keys.
- ToU §11c: **"keep your SSH keys confidential… You are responsible for the activity that happens on or through your LinuxONE Account."**
- ToU §12: the account holder is responsible for all activity, "regardless of whether… undertaken by you… or a third party".
- **No clause bans adding teammates' keys.** The organisers' "one VM per team" instruction implies team access is expected.
- Passing around the owner's **private `.pem` would break "keep your SSH keys confidential"**. Don't do it.
- **VS Code Remote-SSH does NOT work on s390x.** The VS Code Server isn't built for it: IBM Community 2022 thread, Red Hat CRW-9704 "Unsupported architecture", vscode-remote-release feature requests still open, and IBM rejected an Ideas request in Mar 2026.
- **code-server has no s390x release** (checked v4.141.0 assets). Don't plan around either.
- tmux and tmate are in Ubuntu noble's s390x archive (`apt install tmux`).
- `jupyter-collaboration` (real-time co-editing) is pure Python, and its Rust dependency `pycrdt` **ships s390x wheels**. That makes it installable. It is not in the image, though, and is optional.

**Recommended workflow for 25 hours (final call)**
1. **Owner (one person) creates the VM.** Use Ubuntu 24.04-Datathon: the README's primary path, and Docker matches the instructions. Event code SSF2026.
2. **Each teammate runs `ssh-keygen -t ed25519 -C "<name>"` on their own laptop** and sends **only the `.pub`** to the owner over WhatsApp.
3. **Owner adds the keys.** Pick one:
   - **Simple (good enough for 25 h):** append all 3 `.pub` lines to `/home/linux1/.ssh/authorized_keys`. Everyone logs in as `linux1`.
   - **Cleaner (accountability, still ~5 min):** create a user per person:
     - `sudo adduser --disabled-password --gecos "" <name>`
     - put their key in `/home/<name>/.ssh/authorized_keys` (chmod 700 for `.ssh`, 600 for the file, chown to the user)
     - `sudo usermod -aG docker <name>`
     - Pitch it as "least-privilege, per-user audit via `last` / `journalctl`". It doubles as a judge-friendly security screenshot.
4. **Jupyter access: SSH tunnel, don't open the port.**
   - Run `ssh -N -L 38888:localhost:38888 linux1@<IP>` and browse `http://localhost:38888`.
   - The container uses `--network host`, so the tunnel reaches it. Port 38888 stays closed to the internet.
   - If you must open 38888 (e.g. a judge demo), **change the token first** (`--ServerApp.token=<long random>`). The default `Your_Token1` is published on GitHub, so anyone could get code execution on our VM.
5. **Code lives in GitHub (source of truth).**
   - Clone the repo into `~/shared/<repo>` so it appears inside Jupyter.
   - Write logic as **`.py` modules + thin notebooks**. Each person works on their own notebook or branch, because Jupyter doesn't merge and two people saving the same `.ipynb` clobber each other.
   - Do pure-Python, frontend and data-wrangling work **locally on x86**, push, then `git pull` and run on the VM.
   - Add a deploy key or HTTPS token on the VM for push. Use a fine-grained token scoped to the one repo.
6. **Long jobs run in tmux:** `tmux new -s train`. Training survives Wi-Fi drops overnight, and anyone on `linux1` can `tmux attach -t train` to watch.
7. **Back up hourly.** There are no backups (ToU §6). `git push` code. `scp` trained models and outputs to a laptop and to GitHub LFS or a release.
8. **Single point of failure:** only the owner can use the **portal**, e.g. Stop → SHUTOFF → Start when SSH hangs (README FAQ). The owner must stay reachable overnight, or hand over the portal login. Sharing the portal password is a ToU grey area (§12), so prefer the owner staying on call.
   - Keep a `setup.sh` in the repo so the whole stack can be rebuilt on a fresh VM in under 30 min.
   - Ask on Discord whether a teammate may register a backup VM with SSF2026.

---

## Q3. What runs on s390x for AI: realistic in one day?

**Big gotcha (KEEP, checked PyPI JSON today):** the latest numpy 2.5.4, pandas 3.0.6, scikit-learn 1.9.1, xgboost, lightgbm, onnxruntime, torch, tensorflow, llama-cpp-python and psycopg2-binary have **zero s390x wheels on PyPI**. A plain `pip install` **compiles from source**, which takes minutes to hours and needs gfortran/BLAS. **snapml is the exception (s390x wheels).**

So use, in this order:
1. **The prebuilt Jupyter container.** It already has numpy 2.0.2, pandas 3.0.6, scikit-learn 1.9.0, xgboost 3.4.1, torch 2.11 (CPU), tensorflow 2.18.1 + **ibm-zdnn-plugin 2.3.0**, **torch_nnpa 1.5.0**, keras 3.14, onnx 1.22, skl2onnx, tf2onnx, transformers 5.19, huggingface_hub, **llama_cpp_python 0.3.36**, sklearn2pmml, pypmml, rank-bm25, pypdf, seaborn and matplotlib.
2. **conda.** `repo.anaconda.com/pkgs/main/linux-s390x` and `conda-forge/linux-s390x` both respond (checked).
3. **Distro packages** (`apt install python3-sklearn` etc.).
4. **pip from source, last resort.**

**Missing from the image:** lightgbm, onnxruntime, langchain, snapml.

| Thing | Status on s390x | Realistic in a day? |
|---|---|---|
| numpy/pandas/sklearn/xgboost/TF/PyTorch | In the container | **Yes**, the core path |
| Keras on NNPA (ibm-zdnn-plugin) | Preinstalled. Accelerates LSTM, MatMul and similar **only if** `nnpa` is in `/proc/cpuinfo` | **Yes, if** NNPA is exposed (verify) |
| llama.cpp + small Granite (GGUF) | In the container. **Models must be big-endian GGUF**: use `convert_hf_to_gguf.py --bigendian` or the HF "s390x Verified Models" collection. The error "GGUF version extremely large" means a little-endian file. | **Yes**, with small (≤3B, quantised) models. Mind RAM. |
| HF transformers on CPU | In the container | Small models only; slow |
| Snap ML | s390x wheel on PyPI (deps via conda) | Maybe. Not needed. |
| zDLC (ONNX → `.so`, `--maccel=NNPA`) | `icr.io/ibmz/zdlc:5.1.0`. Needs a free **icr.io registry credential**. z17 support since 5.1.0. | Stretch goal; credential lead time is a risk |
| ONNX Runtime | No PyPI wheel. Only via IBM AI Toolkit images. | Avoid; export ONNX but serve with zDLC or the native framework |
| Triton Inference Server | IBM AI Toolkit image exists. Heavy. | No |
| Docker/Podman | Works (README path) | **Yes** |
| PostgreSQL, Redis, nginx, python images | Official Docker Hub images include **s390x** (checked manifests) | **Yes** |
| MongoDB official image | `latest` has **no s390x** | Use Postgres instead |
| Kafka | `apache/kafka` image has **no s390x**. The Java tarball on OpenJDK s390x would work. | Probably skip; use Redis Streams or Postgres LISTEN/NOTIFY for "streaming" |

**Past-participant gotcha (KEEP-ish):** a 2025 Datathon winning team got "strange results" until they moved to PyTorch versions that handle **big-endian** correctly. Lesson: don't load raw binary files or pickles made on x86. Use the container's frameworks, and re-export models on the VM.

---

## Q4. Platform evidence judges can see: credible vs overclaiming

**Credible (do these):**
1. **Containerisation.**
   - Screenshot `uname -m` → `s390x`.
   - Screenshot `docker info | grep -i arch`.
   - Screenshot `docker ps` showing our app + Postgres/Redis + the Jupyter container on s390x.
   - Optional: `docker compose` with resource limits and replicas, plus `docker stats`, as the "scalability" shot.
2. **Hardware crypto (CPACF).**
   - `grep features /proc/cpuinfo` (look for `msa`).
   - `sudo apt install libica-utils && icainfo`: lists AES/SHA/etc. as hardware-backed.
   - Use it for real: encrypt the dataset or model at rest (AES-GCM via `cryptography`/OpenSSL, CPACF-backed) and serve over TLS.
   - The libica docs warn that it **falls back to software silently**, so the claim is "CPACF-capable functions reported by icainfo", not "x faster".
3. **Quantum-safe transport.**
   - Ubuntu 24.04's OpenSSH negotiates the **PQ-hybrid `sntrup761x25519-sha512`** KEX by default. `ssh -v linux1@IP 2>&1 | grep kex` shows it, an honest one-line quantum-safe screenshot.
   - Ubuntu 24.04 ships **OpenSSL 3.0.13** (checked noble s390x), which has **no ML-KEM/ML-DSA** (they arrived in OpenSSL 3.5).
   - **RHEL 9.7+ ships OpenSSL 3.5 with ML-KEM/ML-DSA** (Red Hat docs). So the RHEL9.8-Datathon image likely gives `openssl list -kem-algorithms` → ML-KEM. Verify on the VM. Only matters if we go Theme 2 / PQC.
   - liboqs lists s390x as **Tier 3** ("may or may not work"), so avoid building it.
4. **AI accelerator.** If `nnpa` shows up:
   - screenshot `/proc/cpuinfo` and `tf.config.list_physical_devices()`
   - show the zdnn plugin loaded and our model running with it on
   - and, if ToU-safe (see below), note our app's own inference latency.

**Overclaiming (don't say these):**
- **"Pervasive encryption".** That's a z/OS dataset-encryption term. On Linux it means dm-crypt with CEX protected keys, which we can't show without a crypto card.
- **"HSM / Crypto Express".** `lszcrypt` will almost certainly show no adapters. Check it before mentioning HSMs at all.
- **"IBM Secure Execution / confidential computing".** No evidence it's offered on L1CC. SEL runs on KVM, but L1CC uses z/VM, and IBM sells SEL as Hyper Protect / Confidential Computing Container Runtime.
- **"Spyre accelerator"**: not available. llama.cpp docs say "no current support".
- **"Telum ran our model"** unless the `nnpa` flag and the plugin actually show it.

---

## Q5. Known gotchas
1. **pip builds from source on s390x.** Stay in the container or use conda. Budget for it, or skip any library that isn't preinstalled.
2. **Endianness:** use big-endian GGUF for llama.cpp, and don't carry x86 pickles or `.npy` raw dumps over. Re-train on the VM or export via ONNX/PMML/JSON.
3. **Memory:** the README FAQ has a whole section on memory errors (`docker stats`, `free -h`, restart the kernel, clear outputs). Run **one** heavy kernel at a time. Shut down idle kernels from 4 people.
4. **Disk:** the FAQ suggests `docker rmi` when full. The Jupyter image plus a GGUF model eat disk fast.
5. **Docker permission denied** after `usermod -aG docker`: run `exec bash` or reconnect.
6. **Shared-folder write errors:** `chmod a+w ~/shared` and `chown` to UID 1000.
7. **VM unresponsive:** portal Stop → SHUTOFF → Start. **Only the owner can do this.**
8. **Registration emails** can land in spam or fail. Check the event code. GitHub issue #1 is "can't register", #2 is "Step 5 fails due to authorization" (Docker group).
9. **No VS Code Remote-SSH.** Use Jupyter via tunnel + git.

---

## ⚠ Terms of Use constraints (Marist T&C v9.0, 11 Jun 2021; byte-identical in Wayback snapshots through 31 Oct 2025, so still current)
- **§4 Open source only.** "Using resources… to develop, test, port proprietary software is prohibited." Our repo must be public with an OSS licence. Add an MIT or Apache-2.0 `LICENSE`.
- **§5 No stress, performance or benchmark testing, and "publishing any… benchmark testing results is strictly prohibited".**
  - A CPU-vs-NNPA speed chart or an `openssl speed` table in a public video is a real grey area.
  - IBM's own fraud notebook contains a benchmark cell, and the judges want "compute" evidence, so organisers likely tolerate app-level latency.
  - **Ask `#ibm-z-sme-helpdesk` before publishing any speed comparison.** Frame numbers as "our app's end-to-end latency", not platform benchmarks.
- **§9 No PHI, PCI card data, FERPA or other PII** on the VM. Use **public or synthetic** datasets only. This matters for healthcare and fraud ideas: IBM's synthetic card-txn data is fine, real patient records are not.
- **§11 Keep SSH keys confidential; the account holder answers for all activity.** Add teammates' public keys and never share the private `.pem`.
- **§11 Resource throttling:** Marist can throttle or terminate "excessive" use. Don't leave runaway jobs going overnight.
- **§6 No backups; §7 data cleared at expiry.**

---

## Community consensus
- **HN** (rbanffy, multiple threads 2020–2026, consistently upvoted and repeated): L1CC VMs are z/VM guests. They feel like "a fast two-core machine" with 5+ GHz single-thread speed and fast I/O, and they're time-limited. pm215 and xet7 confirm real OSS projects (QEMU, PostgreSQL) use it for big-endian CI. No dissenting views found.
- **IBM Community** (2025 Datathon winner write-up): the Docker-on-Ubuntu path worked. They saw big-endian surprises with older PyTorch, and training was fast.
- **IBM Community 2022 thread:** VM deleted at expiry with no restore.
- **IBM Community 2022 + Red Hat Jira:** VS Code Remote-SSH fails on s390x.
- **Reddit/Quora:** essentially no L1CC-specific threads. Discord history isn't public. So community input is thin and comes mainly from HN plus the IBM Community.
- **Where community and docs agree:** the platform is fast, the hard parts are packaging (wheels) and endianness, and you must back up your own data.

## Final call (professional + community)
- **Build inside the provided Jupyter container on Ubuntu 24.04-Datathon** and treat GitHub as the backup.
- **Team access:** teammates' public keys (or per-user accounts) plus an SSH tunnel for Jupyter, tmux for long jobs, and no VS Code Remote.
- **Stack:** scikit-learn/XGBoost/Keras plus a small big-endian Granite via llama.cpp. That gives the "predictive + generative" story at low risk.
- **Platform evidence:** s390x containers, CPACF via `icainfo`, PQ-hybrid SSH KEX, and NNPA **only if** `/proc/cpuinfo` shows it.
- **Stay inside ToU §5 and §9:** no published benchmarks, no real PII.

---

## Source ledger

### KEEP
| Source | Supports | Corroborated by |
|---|---|---|
| L1CC Fast Start "deploy-virtual-server.md" (github.com/linuxone-community-cloud/technical-resources, = ibm.biz/BdPcL8) | Registration flow, `linux1` user, key-only, root disabled, only SSH open, iptables paths, single flavor, no backups | ToU PDF §6/§11c; jupyter-lab-ml README |
| jupyter-lab-ml README + README_RHEL + packages.txt (GitHub, fetched raw) | Image name, port 38888, token, `--network host`, SSF2026, 4 notebooks, preinstalled package versions, FAQ gotchas | Guidebook PDF links; notebook raw JSON |
| Raw notebooks `Loan_Approval_Demo.ipynb`, `Fraud_LSTM_Keras_TF.ipynb` | Lab contents: XGBoost + BM25 RAG + Granite/llama.cpp with zDNN build; LSTM + zdnn plugin + benchmark cell | README description |
| LinuxONE Community Cloud T&C v9.0 (tc.l1cc.marist.edu, via Wayback 2025-10-31; same digest 2022–2025) | 120 days, no backups, OSS-only, **no benchmarks**, **no PII**, keys confidential, owner responsible | IBM terms hub (community.ibm.com/zsystems/l1cc/terms) links it; IBM Community "trial expired" thread (deletion) |
| PyPI JSON API (checked 2026-10-16) | No s390x wheels for numpy/pandas/sklearn/xgboost/lightgbm/onnxruntime/torch/tf/llama-cpp-python; snapml and pycrdt have them | Snap ML install docs ("dependencies do not ship s390x wheels on PyPI") |
| llama.cpp `docs/build-s390x.md` (ggml-org) | Big-endian GGUF required, conversion scripts, VXE on z15+, zDNN z17+ WIP, no Spyre | Loan notebook's build notes (`GGML_ZDNN`, OpenBLAS) |
| Docker Hub registry manifests (checked) | postgres/redis/nginx/python have s390x; mongo & apache/kafka don't | n/a (direct primary data) |
| IBM Community 2022 VS Code s390x thread + Red Hat CRW-9704 + IBM Ideas IDZ-I-2351 (Mar 2026) | Remote-SSH unsupported on s390x | code-server release assets have no s390x |
| IBM zDLC GitHub + IBM blog "zDLC 5.1.0" (Jun 2026) | `icr.io/ibmz/zdlc:5.1.0`, needs registry creds, NNPA on z16/z17, z17 support | zDLC 4.2/4.3 blogs (image naming) |
| Red Hat docs (RHEL 9 PQC in OpenSSL) + RHEL Jira 95239/94614 | RHEL 9.7 ships OpenSSL 3.5 with ML-KEM/ML-DSA | OpenSSL 3.5 docs (ML-KEM added in 3.5) |
| Ubuntu packages (noble s390x openssl 3.0.13) + Ubuntu Discourse "PQ support in 26.04" | 24.04 has no ML-KEM; 24.04 SSH default KEX is sntrup761x25519 | OpenSSL 3.5 docs |
| IBM docs: libica/icainfo, "Monitoring CPACF activity" | `icainfo` lists CPACF functions; libica falls back to software silently; cpacfstats is LPAR-only | libica 3.3 PDF (public.dhe.ibm.com) |
| HN comments (rbanffy 2020–2026, pm215, xet7) | z/VM guests, fast ~2-core feel, time-limited | Marist ECC 2017 deck (z/VM); SHARE 2018 abstract |

### WEAK
| Source | Claim | Why weak |
|---|---|---|
| Japanese Speaker Deck "Try LinuxONE Community Cloud" | 2 vCPU / 4 GB / 50 GB | Old (RHEL 7.6 era); SSF2026 flavor likely differs. Verify with `nproc`/`free -h`. |
| jupyter-lab-ml README "z17 Telum II" line | L1CC runs on z17 with NNPA exposed | Marketing context, not a statement about the VM; HN 2024 said z15. **Verify `/proc/cpuinfo`.** |
| z/VM APAR VM66532 + Grafana z/VM NNPA dashboard | z/VM guests can use NNPA | True for the platform; doesn't prove L1CC exposes it |
| "Lab 1 = notebooks 1–3" mapping | Mandatory "multi-model" lab | Inference only; SHARE 2026 BYOD lab title suggests IBM may hand out a separate lab |
| IBM Community 2025 Datathon winner blog (Akshata Pandit) | Big-endian PyTorch issue, Docker workflow | Single team's account, few details |
| Snap ML on PyPI s390x | Installable | Verified wheels exist, deps unproven in this VM |
| My time estimates for the labs | ~1.5–2 h total | No official figure; derived from epochs/steps |

### DO NOT USE
| Claim | Refuted by | Tombstone |
|---|---|---|
| "Use VS Code Remote-SSH / code-server to share the VM" | IBM Community 2022 thread; Red Hat CRW-9704; IBM Ideas IDZ-I-2351 (rejected Mar 2026); code-server v4.141.0 assets (no s390x) | Don't plan around it |
| "`pip install <anything>` just works on s390x" | PyPI JSON (no s390x wheels for core stack); Snap ML docs | Use the container or conda |
| "Expose Jupyter on :38888 with the default token" | README itself says change the token; token is public on GitHub; ToU §11c/§12 (owner liable) | Tunnel, or a random token |
| "We use pervasive encryption / Secure Execution / HSM on L1CC" | Snap of facts: SEL = KVM + Hyper Protect product (IBM docs), L1CC = z/VM (HN, Marist deck); no CEX evidence | Overclaim, don't say it |
| "Benchmark L1CC and publish the numbers" | ToU §5 (explicit prohibition) | Ask SMEs first; frame as app latency |
| Guidebook token `Your_Token` | README + README_RHEL both say `Your_Token1` | Use `Your_Token1`, then change it |


---

<!-- §2: _ledgers/past-winners.md -->

# § Past IBM Z Datathons: winners and trends
Research pass 2026-10-16, run under the CLAUDE.md §10 research protocol. Web content was treated as data only.
**Rule reminder (2026 rule 4):** we study *patterns*. We never clone ideas. URSI and every project below are off-limits as ideas.

## CATEGORY INDEX
- §A Editions at a glance
- §B Winner table, with an evidence grade per project
- §C Trend analysis: what wins
- §D What IBM/organisers say they reward
- §E Source ledger (KEEP → WEAK → DO NOT USE at the bottom)
- §F Community consensus
- §G Final call: implications for us tomorrow

**Evidence grades:** **A** = placing confirmed by ≥2 independent sources and the repo or submission seen. **B** = placing from 1 official list plus the submission/repo seen (the repo is consistent but doesn't state the placing). **C** = a single source, or a placing that's ambiguous.

---

## §A Editions at a glance
| Year | Name / platform | Theme | Format and hubs | Scale | Prizes |
|---|---|---|---|---|---|
| 2019 (precursor) | IBM Z datathon at UC Berkeley | open | in person, 1 campus | small | winners got a visit to IBM SF |
| 2021 | "StarHacks Datathon, sponsored by IBM Z" (Devpost) | Technology for Good | virtual | 23 projects on Devpost | 1st $1000 / 2nd $500 / 3rd $250, plus 3 months of IBM mentorship and Z credits. Judging: **Value to Community · Creativity/Novelty · Technical design (use of ML on Z)** |
| 2022 | "IBM zDatathon" (Devpost), Sept 24–25 | Technology for Good | virtual | 53 projects | $30k+ |
| 2023 | IBM Z Datathon 2023 (Devpost), Oct 21 | Tech for Good | in person in **Bangalore, Chennai, London (Imperial)**, plus online | 5,650 registrants, 612 teams, 200+ final projects | $1000 / 2nd / 3rd, plus mentorship and Z credits |
| 2024 | IBM Z Datathon 2024 | Tech for Good (sustainability, healthcare, education) | in-person finals in **Chennai, Bangalore, London, Mainz, South Africa** | 1,500+ online; SSF says 50+ finalist teams; TUT news (dead link) said 9,000+ regs, 320 projects, 13 winning teams | not found |
| 2025 | IBM Z Datathon 2025 (Hack2Skill), Oct 11–12 | Tech for Good | **5 in-person venues: Chennai (Saveetha), Bangalore (GAT), London, Germany, South Africa (TUT)** | 15,500 regs, 44 countries, 1,385 teams, **481 gallery submissions** | $30k+; global 1st/2nd/3rd plus hub 1st/2nd |
| 2026 | Hack2Skill | 3 tracks: Real-Time AI · AI Secured · Wildcard | 8 hubs, incl. Manchester | — | $50k+ plus the AI Innovation Excellence award |

**No winners list was found for 2021, 2022 or 2024.** Devpost never marked any winner badges. 2024 has no StarHacks page; its URL redirects to the 2025 page.

---

## §B Winner table (every project found)
"L1 depth" means how deeply the team used LinuxONE: **0** = no evidence it ran on LinuxONE · **1** = ran a notebook on the L1CC Jupyter image · **2** = served a model/API from the L1CC VM, or did s390x-specific work · **3** = containers, crypto or scale exploited and shown.

### 2025 (official list: starhacks.org/2025-ssf-ibm-z-datathon; submissions pulled from the public Hack2Skill gallery API)
| Team | Place / hub | Project · problem | Data | Models / stack | L1 depth | Repo | Grade |
|---|---|---|---|---|---|---|---|
| Life Aspirant's (ONL319) | **Global 1st** | Plastic pollution in water: detect, track and forecast | satellite/drone imagery (proposed), plus IoT buoys (concept) | DL image detection in 1 notebook, plus an index.html. The 89%/95%/40% figures in the pitch are claimed, not shown | 1 (no L1 evidence in repo) | github.com/teja-cmd/Plastic-Detection-in-Water-Resources (4 files) | B |
| Hackasaurs (ONL487 on list; ONL585 in gallery) | **Global 2nd** | Demand forecasting for public meal programmes, to cut food waste | Walmart + food-sales + time-series data, synthetically enriched | LightGBM (Tweedie), XGBoost, LSTM; 70+ engineered features; R² 0.85–0.92; 9 dashboards; React frontend | 1–2 (README has a "#CodingInLinuxOne" screenshot) | github.com/Yukesh-30/IBM_DATATHON_HACKASOURS | B |
| Gradient Ascent (ONL486) | **Global 3rd** | OcuGuard AI: retinal photo → multi-label eye-disease triage (Urgent / Non-urgent / Normal) plus an advisory report | retinal fundus images | multi-label CNN | ? | github.com/DhruvShetty21/IBM_Hackathon (**404 now**) | B− |
| Tech Titans (SAV077) | **Chennai 1st** | TradeSentinel: trading-fraud and collusion detection with an "IBM Z Crypto-Express-inspired" HMAC rolling-key trust seal and an immutable ledger | behavioural/trading (simulated) | Graph-ML, transformer ensemble, behavioural biometrics, LLM agent layer; Next.js + Genkit | 0–1 (abstract admits: *"we have not used IBM features since they are not free"*) | github.com/inesh-2384/Trade-Sentinel | B |
| BIG IRON (SAV106) | **Chennai 2nd** | Heart MRI classifier as a clinical second opinion | cardiac MRI | TF/Keras CNN, Flask, IBM Cloud COS + Db2, XAI heatmaps | 1 (IBM Cloud, not deep L1) | github.com/ShivrajRajasekaran/AI-Powered-Heart-MRI-Classification-for-Clinical-Decision-Support (README: *"2nd Place — IBM Z Datathon 2025, Chennai In-Person Track"*) | **A** |
| RUNTIME TERRORS (GAT097 on list) | **Bangalore 1st** | **Ambiguous.** The gallery's GAT097 is "Dedcell" (passwordless auth: WebAuthn + behavioural keystroke one-class SVM). "RUNTIME TERRORS" is GAT149 (alternative credit scoring for the unbanked: RF/XGB/NN + fairness module + "LinuxONE encryption"). Also SAV156 Runtime Terrors (weWalk women's safety map) | — | — | ? | GAT149 = Drive link; GAT097 = github.com/jejo205713/PBauth | C |
| YuktiX (GAT096) | **Bangalore 2nd** | Fog/rain intensity map + weather anomaly detection | **synthetic** weather for 5,000 locations | RandomForest (fog class) + IsolationForest (anomaly); map heatmap | 1 | github.com/Harini-j-2005/IBM_Project (5 files; boilerplate README) | B |
| IBMLOND015 "Medikate" | **London 1st** | Risk of patients missing doses of existing prescriptions (adherence, *not* diagnosis); "privacy-safe" | tabular MEDDATA.csv | Tabular Transformer + class-imbalance handling; FastAPI served **on LinuxONE**; React dashboard with CSV upload | 2 (README also *claims* Confidential Computing / OpenShift; no evidence they were built) | github.com/Neesay/IBM-Z-Datathon-2025-Team-15-EdizSlow | B |
| AlphaPeterGamma "CrisisLens" | **London 2nd** | Riot early warning from X/Twitter discourse → crisis heatmaps | cleaned Twitter datasets + event data | PoliBERTweet embeddings → KNN influence graph → **attention GNN**; heatmaps | 1–2 (repo: *"all code was written on the IBM Z jupyterlab environment"*) | github.com/notacountry/IBM-Z-Datathon (desc: *"We won 2nd place"*) | **A** |
| IBMGER004 | **Germany 1st** | Interstate conflict early warning from trade interdependence | UCDP conflict levels, UN trade, IMF GDP | simple NN → LSTM | 1 ("train our models on IBM Z") | gitlab.rlp.net/kzeeb/ibm-z-ibmger004 | B |
| Theto Maunatlala "AnalytIQ" — **URSI** | **South Africa 1st** (and the guidebook's showcase example) | Urban Route Safety Index: roads labelled Safe/Moderate/Risky so routing can prefer the safest path | SAPS crime stats (quarterly xlsx) + OSM roads, streetlights, cameras, police, hospitals, bus stops (Johannesburg geojson) | weighted scoring / logistic regression; geopandas, osmnx, folium map; **IBM Watson Studio**; src/*.py files are empty | 0–1 | github.com/thetomaunatlala-777/AnalytIQ--Urban-Route-Safety-Index-URSI- | **A** (starhacks list + guidebook description + matching gallery entry) |
| Izimpisi ze-Data (TUT041) | **South Africa 2nd** | Public-fund misallocation / corruption detection (SA health sector) | **synthetic** (couldn't find SA data) | anomaly detection + ML on "IBM Z and LinuxONE" | ? | github.com/Matooloose/Prince (**404 now**) | B− |

Also seen, not placed (context only): Team Oasis (GAT, lake encroachment CNN in Docker on L1CC). Its IBM blog says *"we also won the challenge"*, but the year is unclear and it is not on the 2025 list (grade C). HaloMap (London: night-safety router, React + FastAPI + SQLite, `cost = distance × (1 + λ·danger)`) did **not** place. SurakshaMap and weWalk (Chennai safety maps) did not place. So "safety routing" alone does not win.

### 2023 (official list: starhacks.org/2023ibmzdatathon; projects on Devpost ibm-zdatathon-18843)
| Team | Place / hub | Project | Stack | L1 depth | Repo | Grade |
|---|---|---|---|---|---|---|
| CodeCatalysts (Team ON24) | **2nd** (online) | Hate-speech detector / AI moderator | BERT (bert-base-uncased) fine-tuned in PyTorch, weighted BCE, ~25k Kaggle labelled tweets, 95% accuracy; REST API added after the event | 2. Deployed inference on L1CC (s390x Docker Ubuntu), <1 s inference; **had to fix big-endian weight loading** | github.com/chrehall68/SSF23-CodeCatalysts | **A** (starhacks + Devpost + author's IBM blog) |
| Uncalled coders (Team SRM15) | **2nd** | Fraud detection in transactions | single notebook; generic RF/NN; template README | 1 | github.com/sagar3501/Fraud-Detection-in-Transactions-Uncalled-Coders-Team-SRM15 | B |
| Data Detectives | **London in-person 1st** | not found | — | — | — | C |
| Carmex – Lambda Prime | **Bangalore in-person 1st** | not found | — | — | — | C |
| RIP_ENGINEERS; Ctrl Alt Del ("Mentor" award) | 1st (hub unclear) | not found. Search summaries attributed "urban waste classification" to Ctrl Alt Del, but this was **not verified** | — | — | — | C |
| The Code Wizards; Data_R_Us | 2nd | not found | — | — | — | C |
| Starfall stallions | **Chennai in-person 3rd** | not found | — | — | — | C |
| Matt Gummow / Ben James / Sarah Matthews / Alexander Timms (Imperial) | "one of two UK winners", 2nd place | Tweet → charitable-cause classifier → links to relevant charities | LLM-based data labelling, XGBoost tuning, embedding topic classification, BeautifulSoup scraping, on LinuxONE | 1–2 | not found | C (search summary of a LinkedIn profile; LinkedIn blocked the fetch) |
| (Jason Li, "GSE UK – IBM Z Datathon winners") | winner, UK | unspecified neural-net project on L1CC Jupyter (TensorFlow) | — | 1 | — | C |

### 2021 (Devpost starhacks-datathon)
| Team | Place | Project | Stack | L1 depth | Repo | Grade |
|---|---|---|---|---|---|---|
| Team 34 "Fantastic Four" (VIT Chennai) | **3rd ($250)** | Farmer's Friend: crop recommendation + clustering for mixed cropping | rainfall/climate/fertiliser data merged from GitHub; LogReg / Decision Tree / SVM, decision tree best (99%) | 1 | github.com/sayantann11/IBM-z-DATATHON | B (Devpost project + VIT news snippet; the $250 matches the 2021 3rd prize; the VIT page refused connection) |

### 2019 precursor (UC Berkeley, princessleia.com, Dec 2019)
Winners: student financial help · wildfire modelling · homelessness support spending. These ran in Jupyter on IBM Z. Grade C (1 source), but it carries a useful judge-behaviour quote (§D).

---

## §C Trend analysis: what wins (based on 2025, the only year with full submission data)
**Field baseline (all 478 substantive 2025 abstracts, keyword tally):** environment/disaster 32% · health 32% · fraud/finance 19% · education 16% · agri/food 13% · safety/crime 5% · cyber 6% · GenAI/LLM 4% · **containers <1% · s390x/Telum/Snap ML/ONNX <1%**.

1. **Domain: social good beats commerce, and the problem is told as a human story.** All 12 placed 2025 projects frame a vulnerable group or a public harm: women commuters, patients, the unbanked, riot-hit minorities, conflict regions, public meal programmes. Pure-finance ideas placed only when framed as protection (TradeSentinel protects retail traders; the credit idea is about inclusion). Health (3 of 12) and environment/disaster (3 of 12) match the field mix. **Safety and early-warning framings are over-represented among winners** (URSI, CrisisLens, IBMGER004 conflict, TradeSentinel) compared with 5% of the field.
2. **"Real-time / early warning / decision support" is the dominant narrative shape.** It shows up in ~8 of 12 winners (forecast, flag, triage, warn). This maps directly onto the 2026 Theme 1 ("Detect. Decide. Respond.").
3. **ML is mostly classical or mid-level DL. GenAI is rare among winners.** Winners used LightGBM/XGB/RF/IsolationForest (Hackasaurs, YuktiX, URSI), CNNs (BIG IRON, OcuGuard), LSTM (IBMGER004), BERT (CodeCatalysts 2023), Tabular Transformer (Medikate), GNN + BERTweet (CrisisLens). Only 4% of 2025 abstracts used GenAI; no podium winner was GenAI-centric (TradeSentinel's LLM agent layer is an add-on). The technical ceiling among winners is "a GNN on Twitter embeddings", which is modest. **Sophistication is not what separated winners.**
4. **LinuxONE depth among winners is shallow.** No winner shows containers, crypto (CPACF/HSM), Snap ML, ONNX/zDNN or scaling evidence. Best cases: a FastAPI model server on the L1 VM (Medikate), all development in the L1 Jupyter (CrisisLens), and s390x big-endian fixes (CodeCatalysts 2023, Team Oasis). Several winners show **zero** L1 evidence (URSI used Watson Studio; BIG IRON used IBM Cloud; Tech Titans admitted no IBM features). The 2026 rubric now explicitly asks for "security, scalability, containerisation, compute" and screenshots. **Real depth here is a near-empty lane** (<1% of the field), and that is the clearest differentiator.
5. **Synthetic or merged public data is accepted.** YuktiX (fully synthetic weather), Izimpisi (synthetic finance), Hackasaurs (synthetically enriched) all placed. Judges did not punish synthetic data when it was disclosed. Real government open data (SAPS, UCDP, UN, IMF, OSM) shows up in the stronger winners (URSI, IBMGER004).
6. **Presentation and visible output carry a lot of weight. Code completeness matters less.** Winners consistently shipped a *visual artefact*: a colour-coded safety map (URSI's own "Wow factor" section), crisis heatmaps, fog heatmaps, dashboards, triage reports. Repos are often thin (4–5 files, empty src/ files, boilerplate READMEs, notebooks only). Judges evidently scored from the 3-minute video and deck. Clear "who benefits" sections (URSI lists audiences) and concrete impact numbers (Hackasaurs: ₹700 crore losses, R² 0.85–0.92) recur.
7. **Common weaknesses, even among winners:** inflated, unsourced metrics (Life Aspirant's "89% / 95% / 40%"); aspirational "Why IBM Z" claims (Confidential Computing / OpenShift / Crypto Express "inspired") without implementation; repos that are now 404 (2 of 12); messy notebook-only repos; synthetic data. **Honourable vs podium:** hub podiums go to "clear social problem + working demo + map/dashboard". Global podiums had the most polished, end-to-end story (multi-dataset pipeline + many dashboards for Hackasaurs; triage + advice report for OcuGuard).
8. **Hub competition is shallower than global.** Hub podiums include very simple projects (YuktiX: synthetic data + RF). The London hub was won by a working FastAPI + React tool on a tabular model. A complete, well-pitched, honest build is competitive at a hub.

---

## §D What IBM / organisers say they reward (quotes)
- 2021 Devpost judging criteria: *"Value to Community · Creativity/Novelty of the idea · Technical design (Use of ML on Z technology)."* This is the same skeleton as the 2026 rubric, plus Execution.
- 2019 Berkeley judge (princessleia.com): IBM's judging favoured projects that **used large datasets or processed real-time data**, *"since the mainframe's strength is quickly crunching data"*. The projects using that capability *"were the ones that stood out."*
- 2026 guidebook: *"Your solution should centre on a problem that matters, not just a technical showcase"*; the Technical criterion names *"security, scalability, containerisation and compute resources"*; and the video must *"show the LinuxONE instance and the model."*
- SSF page: the datathon exists partly to *"pre-empt customer objections about lack of IBM Z talent"*. So **advocacy for Z** (why Z specifically) is a goal for the organisers, and there's a "Best IBM Z Advocacy" special award.
- GSE UK 2024: UK/Europe hub winners get to present at the GSE UK conference. Judges value winners who can *"share their learnings"*.

---

## §E Source ledger
### KEEP (corroborated or primary)
| Source | Used for | Corroborated by |
|---|---|---|
| starhacks.org/2025-ssf-ibm-z-datathon (official SSF page) | 2025 global and hub winners; 2025 stats | Hack2Skill gallery entries with the same names; BIG IRON and CrisisLens repos self-report their places; the guidebook's URSI text |
| Hack2Skill public gallery API (`/api/v1/submission/datathon-2025/peer-review/team/{id}`, linked from guidebook p.6 "2025 Project Submissions") | problem, solution, repo and video for all 481 2025 submissions | starhacks list; repos |
| Guidebook 2026 PDF (local) | URSI description; rubric; 2026 prizes and hubs | URSI gallery entry + repo |
| github.com/notacountry/IBM-Z-Datathon | CrisisLens 2nd, London; built in L1 Jupyter | starhacks London 2nd = AlphaPeterGamma |
| github.com/ShivrajRajasekaran/…Heart-MRI… | BIG IRON 2nd, Chennai; stack | starhacks |
| github.com/thetomaunatlala-777/AnalytIQ--URSI- | URSI stack and data | guidebook + starhacks + gallery |
| starhacks.org/2023ibmzdatathon | 2023 team placings | Devpost 2023 (CodeCatalysts, Uncalled Coders) + IBM blog |
| community.ibm.com, Christopher Eliot Hall, 2024-04-10 | CodeCatalysts stack; big-endian fix; <1 s inference | Devpost + GitHub chrehall68 |
| Devpost galleries (starhacks-datathon = 2021, ibm-zdatathon = 2022, ibm-zdatathon-18843 = 2023) | edition formats, prizes, 2021 judging criteria, project details | starhacks pages; SSF page |
| starhacks.org/ibm-z-datathon-2023 | 2023 scale (5,650 regs, 612 teams) | Devpost 2023 |

### WEAK (single source, or partly unverified)
| Source | Issue |
|---|---|
| shooting-stars-foundation.org/ibm-z-datathons | 2024 stats (1,500+ online, 50+ finalists, 5 hubs) come from one org page; they conflict with the TUT "9,000 regs / 13 winners" snippet |
| chennai.vit.ac.in "Third Place" | refused connection; claim taken from a search snippet only (consistent with the Devpost 2021 $250 3rd prize) |
| tut.ac.za news 428 (TUT 36 2nd for SA, 2024) | page is now 404; search snippet only |
| community.ibm.com Akshata Pandit 2025 (Team Oasis "won") | year and place unspecified; not on the 2025 list |
| community.ibm.com MingMay Pang ×2 (2024-02) | byline ≠ author; no team or place details |
| LinkedIn (Gummow, Timms, Rajsheker 2024 3rd global) | blocked (HTTP 999); search summaries only |
| princessleia.com 2019 | one blogger; useful judge-behaviour quote but a different (precursor) event |
| HackerEarth IBM Z Student Contest criteria (2021) | different contest (z/OS skills); only a proxy for IBM judging taste |
| Saveetha pages (2023, 2024, 2025) | hosting facts only; no winners |

### DO NOT USE (refuted or contradicted)
| Claim | Why | Refuting sources |
|---|---|---|
| "Hackasaurs won 1st prize in 2025" (a search-engine summary) | The official list has Life Aspirant's 1st and Hackasaurs 2nd | starhacks 2025 page; layout re-checked in raw HTML |
| "Ctrl Alt Del won London 2023 with urban waste classification" (a search-engine summary) | The starhacks 2023 page puts *Data Detectives* at London 1st; Ctrl Alt Del is listed with "Mentor"; no source for the waste project was found | starhacks 2023 page |
| Life Aspirant's metrics "89% detection / 95% precision / 40% efficiency" | Unsourced pitch claims; the repo is a single notebook with no evaluation shown. Do not quote them as achieved results | the repo itself |
| Team-ID prefixes on the starhacks 2025 list as identifiers (e.g. GAT097 = Runtime Terrors) | Gallery IDs disagree (GAT097 = Dedcell; Hackasaurs = ONL585). Use team names, not IDs | Hack2Skill gallery |

---

## §F Community consensus
- **Reddit / HN / StackExchange / Quora:** no threads found on the IBM Z Datathon. The community signal is thin.
- **Participant write-ups (IBM Community blogs ×4, Medium, LinkedIn summaries)** repeat the same points, all from winning or happy teams, so treat them as biased:
  1. L1CC is easy to set up (web console, Jupyter image, Docker preinstalled).
  2. Inference/training was "faster than my laptop".
  3. **s390x big-endian bites:** model weights/PyTorch give garbled outputs until you save big-endian weights or use a newer PyTorch. Reported independently by CodeCatalysts (2023) and Team Oasis (2025), so this is **KEEP**.
  4. Collaboration on L1 Jupyter is awkward. CrisisLens: *"all code was written on the IBM Z jupyterlab environment, which made collaboration on the same file impractical."*
- **Contrasting view:** none found. Nobody reports the judges rewarding deep platform work, because no winner did it.

---

## §G Final call (professional evidence + community evidence, aggregated)
**Top 6 trends to act on (patterns, not ideas):**
1. **Lead with a vivid, named human harm and a "who benefits" list.** Every winner did this; Value to Community is worth 10 of the 40 points.
2. **Use a real-time / early-warning / decision-support shape** (detect → score → act). It's the most common winner narrative, and it is literally 2026 Theme 1.
3. **Use a modest, well-justified model on real public data, plus one visible artefact** (a map, dashboard or triage report). Winners won on clarity and the demo, not on model novelty. Synthetic data is tolerated if disclosed.
4. **Real LinuxONE depth is the open lane.** No past winner showed containers, crypto or scale, while <1% of 2025 entrants even mentioned them, and the 2026 rubric now explicitly scores them and asks for screenshots. Serve the model from a container on the L1 VM and show s390x evidence (`uname -m`), encryption and a throughput number on screen. This is the cheapest way to outscore past winners on Technical.
5. **Back up every "Why IBM Z" claim.** Past winners claimed Confidential Computing, OpenShift and Crypto Express without building them. The 2026 judges (IBM SMEs) will see through unproven claims, so show it or don't claim it.
6. **A polished 3-minute video plus an honest repo beats a sprawling repo.** Judges score from the video and deck. Keep metrics real and sourced (avoid the Life Aspirant's pattern), keep the repo public (2 of 12 winner repos have since gone 404), and plan for the big-endian gotcha and the shared-Jupyter collaboration pain on day 1.

**Confidence:** high for 2025 (official list + full submission data + repos). Medium for 2023 (names known, few projects). Low for 2021, 2022 and 2024 (almost no winner data exists publicly).


---

<!-- §3: _ledgers/theme-research.md -->

# § Theme research — 2025–2026 breakthroughs (IBM Z Datathon 2026)
Pass date: 2026-10-16 (night before kick-off). Protocol: CLAUDE.md §10. Every source below was fetched or surfaced by search on this date; claims marked "(author claim)" are not independently replicated.
Recency: 2025–2026 preferred. Extended to 2022–2024 only for foundations with no newer replacement (ACI, BAF, AMLworld, Multi-GNN, RMIA, Stadler); each is flagged.

---

## 0. Platform facts that gate everything (read first)
- **The provided image is richer than expected.** `jupyter-lab-ml` `packages.txt` pins: `torch==2.11.0+cpu`, **`torch_nnpa==1.5.0`**, **`ibm-zdnn-plugin==2.3.0`** (TensorFlow → NNPA), `tensorflow==2.18.1`, `xgboost==3.4.1`, `scikit-learn==1.9.0`, `onnx`, `skl2onnx`, `tf2onnx`, `transformers==5.19`, `safetensors`, `llama_cpp_python`, `sklearn2pmml`, `networkx`. **Not present:** lightgbm, river, MAPIE, PyG, opacus, diffprivlib, presidio. These need `pip install` (pure-Python ones are fine; compiled ones are a risk on s390x).
- README says the image targets **z17 / Telum II on-chip AI accelerator**. Whether *our* VM exposes NNPA is unconfirmed (a 2025 IBM Community page still described the cloud as LinuxONE III). **First check on the VM: `grep -o nnpa /proc/cpuinfo`.** If present, running inference through `torch_nnpa` / zDNN is the single strongest "why LinuxONE" story for criterion 3.
- **Big-endian (s390x) risk:** safetensors/HF weights are stored little-endian; TF and llama.cpp both needed explicit byteswap fixes for s390x. Any pretrained-weight model (TabPFN, TTM, GLiNER, Granite HAP) must be smoke-tested on the VM in the first hour, with a non-pretrained fallback.
- PyTorch s390x wheels were nightly-only as of mid-2025 (llama.cpp commit), so **do not `pip install torch`**; use the image's build.
- Built-in demo notebooks already cover: fraud LSTM, churn RF, MNIST→ONNX, and **loan approval = ML score + RAG + Granite on llama.cpp**. That last one *is* the "predictive decides, LLM explains" pattern. Copying it is not novel (criterion 2 scores "commonly available" 0–3). We have to go past it.

---

## THEME 1 — Real-Time AI for Critical Decisions

### F1.1 Online / adaptive conformal prediction with abstention → human deferral  ★ top pick
- **Method:** wrap any scorer (XGBoost) with conformal prediction. In streaming, use **Adaptive Conformal Inference (ACI)**, which updates the miscoverage level online so coverage holds under drift without exchangeability. Newer variants: **Error-quantified CI** (continuous feedback instead of 0/1; arXiv 2502.00818, 2025) and **retrospective-adjustment online CI** (faster recalibration after shifts; arXiv 2511.04275, Nov 2025). Decision rule: if the prediction set is `{fraud}` → block; `{legit}` → pass; `{fraud, legit}` (ambiguous) → **defer to analyst**. That turns "confidence" into a calibrated, auditable abstention budget.
- **Imbalance matters:** for rare-event classes, use **Mondrian (class-conditional) CP**. A 2026 multi-domain benchmark (arXiv 2607.27143, 15 imbalanced datasets, 3,150 runs) reports marginal CP's minority-class coverage dropping "as low as 0.5%", and Mondrian lifting it by ~62 pp on average. Mondrian + cost-controlled abstention lowered expected decision cost under realistic review budgets (preprint).
- **Evidence:** ACI foundation (Gibbs & Candès, NeurIPS 2021, extended 2022) + two independent 2025 follow-ups → KEEP. Mondrian-for-imbalance → corroborated by the 2026 benchmark plus long-standing Vovk Mondrian theory → KEEP (the specific numbers are WEAK, single preprint).
- **Library:** **MAPIE v1.x** (pure Python/sklearn; note `MondrianCP` class temporarily removed in v1, with a manual tutorial instead), or **crepes** (Mondrian native). ACI is ~20 lines of numpy. All pure Python → **s390x: yes, same day.**
- **Dataset:** Feedzai **BAF** (NeurIPS 2022, 6 variants with built-in temporal shift + bias; Kaggle), IEEE-CIS, or IBM **TabFormer** synthetic card transactions.
- **Rubric fit:** C1 (safe human-in-the-loop for high stakes), C2 (calibrated deferral under drift is rarely in student builds), C3 (cheap per-event inference = can show throughput on LinuxONE).

### F1.2 Conformal-based deferral to *multiple* experts, training-free
- **Method:** use conformal prediction sets to route each uncertain case to the human expert best at separating the remaining plausible labels ("segregativity"). No L2D retraining when the expert pool changes.
- **Evidence:** Bary, Macq, Petit, arXiv 2509.12573 (v3 Mar 2026), CIFAR10-H + HAM10000. Author claim: up to 91.3% fewer training labels per expert, ~100× less training time. Corroborated in direction by Fang & Nalisnick (conformal rejector, NeurIPS-W 2024 → TMLR 2026) and Straitouri et al. (showing sets to humans improves team accuracy). **WEAK→KEEP for the concept, WEAK for the numbers** (preprint, image datasets).
- **Library:** no code linked; implementable on top of MAPIE/crepes in a few hours. s390x: yes.
- **Demo:** simulate 2–3 "analyst" profiles with different per-class accuracy; route the deferred queue. Gives a unique triage-routing visual.
- **Rubric fit:** C2 novelty (genuinely 2025-new), C1.

### F1.3 Label-delay-aware drift monitoring (score-distribution monitoring)
- **Method:** in fraud, ground-truth labels arrive days to weeks late (chargebacks). So monitor **drift in the model's score distribution without labels**, and trigger ACI recalibration or retraining when it moves. ADWIN-triggered retraining cut retrains substantially with little AUC loss in a 2025 streaming fraud framework.
- **Evidence:** SAMM (Feedzai, KDD-W 2019, label-free monitoring; foundation, extended) + ROSFD (arXiv 2504.10229, 2025, ADWIN best of DDM/EDDM/ADWIN) → KEEP for the approach. Caveat from benchmarks: drift-detector evaluation is messy. A 2026 framework (Cerqueira, Gomes, Bifet et al., arXiv 2606.07789) recommends SEED/STEPD/ABCD as robust defaults. Giobergia et al. (KDD-W 2024) show common detectors miss subpopulation-local drift. So **don't claim "our detector catches all drift"**.
- **Library:** **River** (ADWIN, Page-Hinkley; pure Python + some Cython; s390x install plausible, test early). Or hand-roll ADWIN/KS-test on score windows with scipy (already in image).
- **Dataset:** BAF (months 0–7 have designed temporal shift) is ideal.
- **Rubric fit:** C3 (production realism), C1.

### F1.4 Multigraph GNNs for AML / transaction-network risk
- **Method:** IBM Research's **Multi-GNN** adds port numbering, ego IDs, and reverse message passing so a message-passing GNN can detect directed subgraph patterns (cycles, fan-in/fan-out, scatter-gather) in multigraphs. Author claim: up to +30% minority-class F1 vs standard MPNN on AML. **MEGA-GNN** (arXiv 2412.00241) reports a further ~13% over it.
- **Evidence:** Egressy et al., AAAI 2024 (ETH + IBM). Dataset paper: Altman et al., **NeurIPS 2023 D&B** (IBM AMLworld synthetic AML, ground-truth laundering patterns). Two independent follow-ups build on it → KEEP (extended to 2024; foundational, no newer replacement).
- **Library:** official code exists (GitHub IBM/Multi-GNN, not verified in this pass). Needs **PyTorch Geometric, which is not in the image**; compiling torch-scatter/sparse on s390x is a real risk. **s390x: risky.** Fallback that runs: networkx/numpy graph features (fan-in/out, cycle counts, ego degree in a time window) fed to XGBoost. The AMLworld paper itself used GBT baselines.
- **Dataset:** **IBM AMLworld (HI-Small / LI-Small)**, Kaggle. An IBM dataset → Best IBM Z Advocacy angle.
- **Rubric fit:** C3 (graph + IBM lineage), C2 if real GNN runs; C1 (AML harms).
- **Note:** TGB 2.0 (NeurIPS 2024) finds simple heuristics often rival complex temporal GNNs, and most methods fail at scale. That supports doing graph-feature engineering + GBT in a 25-hour build.

### F1.5 Tiny pretrained forecasters for early warning (IBM Granite TTM)
- **Method:** **Tiny Time Mixers** (~1M params, IBM Research) do zero/few-shot multivariate forecasting. Author claim: 4–40% better than popular benchmarks, runs on CPU. r2 > r1 by >15%. r2.1 added daily/weekly resolution.
- **Evidence:** NeurIPS 2024 (peer-reviewed) + IBM model cards + tutorial. Independent corroboration is thin in this pass (TabPFN-TS ranks highly on fev-bench too, so TTM is not uniquely best) → **WEAK-to-KEEP**. Use as a fast baseline, not a headline claim.
- **Library:** `granite-tsfm` (pip; pure-Python on top of torch/transformers, both in image). **s390x: plausible but weight-endianness must be tested**. 1M params makes it a perfect candidate to push through NNPA.
- **Dataset:** anything streaming: transaction volume per merchant, server metrics (NAB anomaly benchmark), grid load.
- **Rubric fit:** C3 (IBM model on IBM hardware), C1 if the early-warning story is strong.

### F1.6 Tabular foundation models (TabPFN v2 → TabPFN-3)
- **Method:** a transformer pre-trained only on synthetic data does in-context prediction on a new table in one forward pass, no tuning.
- **Evidence:** Hollmann et al., **Nature 637 (Jan 2025)**. Author claim: beats 4-hour-tuned GBT ensembles on ≤10k rows in seconds. Independent **TabArena** (arXiv 2506.16791, living benchmark): TabPFNv2 strong (avg rank ~3.1 ensembled) but only evaluated on the subset it fits. Tuned+ensembled RealMLP/TabM/LightGBM topped v0.1. **TabPFN-3** (arXiv 2605.13986, May 2026) claims scaling to 1M rows (on an H100). Practitioner caveat: results depend on hidden defaults (dataframe vs numpy, categorical handling); newest weights are non-commercial. → **KEEP for small data; WEAK for "beats GBT generally".**
- **Library:** `tabpfn` pip. **s390x: risky** (HF weight download, possible gating, endianness, CPU-only means slow beyond a few thousand rows). Not a core dependency for a 25-hour build.
- **Rubric fit:** C2 if it works; good pair with conformal (calibrated probabilities, per a 2026 preprint).

### F1.7 Hybrid: predictive model decides, LLM explains (with guardrails on the explanation)
- **What's new (2025–26):** evidence that **LLM-written explanations drift from the model's real reasons**. LLMs sometimes override contradictory SHAP values with prior knowledge (arXiv 2412.10220). LLM self-stated feature impacts diverge from SHAP on financial tabular data (arXiv 2512.00163). Self-explanations mismatched the data in 14/20 tabular tasks (arXiv 2608.02412). → KEEP as a *caution*: the novel twist is to **verify the LLM narrative against SHAP** (rank/sign check, as 2412.10220 proposes) before showing it.
- **Library:** image has `llama_cpp_python` + Granite (from the loan demo); SHAP via `pip install shap` (has C ext; test) or XGBoost's built-in `pred_contribs=True` (no install).
- **Rubric fit:** C2 (faithfulness check beats the stock loan demo), C4 (good demo moment).

---

## THEME 2 — AI Secured: Innovation Without Exposure

### F2.1 Confidential computing on s390x: IBM Secure Execution for Linux  ★ IBM-Z-native
- **What:** hardware-isolated, encrypted, attested VMs on z15+/LinuxONE III+, so the hypervisor/admins can't read guest memory. LinuxONE 5 adds vendor-generic images that tenants personalize with their own secrets. IBM's Confidential Computing Container Runtime / Hyper Protect builds on it.
- **Evidence:** IBM docs + FOSDEM 2023/2025 + KVM Forum 2022 (attestation, confidential dumps). Applied to AI: a 2026 preprint (arXiv 2608.21393) on a Spyre-accelerated RAG kept fully inside one LinuxONE under Secure Execution; author claim <2 s end-to-end, "up to 20×" vs off-platform (single non-peer-reviewed source → WEAK for numbers).
- **s390x feasibility:** we almost certainly **can't enable SE on a community-cloud guest** in a day. Use it as the *architecture story* (explain it, cite it, screenshot what exists), not a feature we claim to have run.
- **Rubric fit:** C3 "fully exploits security" — the strongest *why-IBM-Z* argument in Theme 2.

### F2.2 Homomorphic-encryption inference with IBM HElayers  ❌ CORRECTED 2026-10-16: does NOT install on s390x (see critic-feasibility.md)
> **Correction:** a live PyPI check found only pyhelayers 1.5.5.1–1.5.5.4, all x86_64. The "s390x cp311 wheel 1.5.4.0" claim below is **DO NOT USE**. Use Paillier via `phe` (pure Python: encrypted features × plaintext linear weights) instead.
- **Method:** score an encrypted transaction/patient vector with a logistic-regression/small-NN model under CKKS. The server never sees the plaintext.
- **Evidence:** IBM developer blog states **Python & C++ kits for x86 and s390x**. PyPI lists a **`pyhelayers` s390x manylinux wheel (cp311, v1.5.4.0)**. A CERN mirror lists only x86 for 1.5.5.3, so s390x lags. IBM `fhe-toolkit-linux` Docker has encrypted NN-inference demos. → KEEP (vendor sources, but two independent listings confirm the s390x wheel).
- **Caveats:** Community Edition = **non-commercial license** (fine for a datathon, must be disclosed/linked). Check that the image's Python is 3.11 (the wheel is cp311). Concrete-ML / OpenFHE / TenSEAL have no s390x wheels → **don't plan on them**.
- **Dataset:** any small tabular set (UCI credit default, BAF subset, diabetes).
- **Rubric fit:** C2 + C3 strongly (FHE on IBM hardware with IBM's own library); C1 if framed as "bank scores you without seeing you."

### F2.3 DP synthetic data — with an honest privacy *audit*
- **Method:** generate DP synthetic tabular data with marginal-based mechanisms (**AIM / MST**, Private-PGM), then **audit it with membership-inference attacks** rather than trusting it.
- **Evidence:**
  - Benchmarks: Chen et al. (arXiv 2504.14061, ICLR 2025 listing) find **no universal winner**; statistical methods win on utility, ML methods on efficiency. A 2026 fairness benchmark says utility benchmarks consistently show marginal-based > DP-GANs. **Tab-PE** (Microsoft, ICML 2026 listing) claims up to +10% accuracy over AIM on high-order-correlation data.
  - Audit need: **Synth-MIA** (arXiv 2509.18014, 13 attacks, sklearn-like API): higher synthetic quality ⇒ more leakage; similarity-based privacy metrics correlate weakly with MIA; **PATEGAN can fail to preserve privacy**. Consistent with Stadler et al. (USENIX Sec 2022): non-DP synthetic data ≠ anonymous.
  → KEEP (≥2 independent sources each side).
- **Library:** `dpmm` (arXiv 2506.00322: PrivBayes/MST/AIM, claims +1.5% over private-pgm), `private-pgm`, **IBM `diffprivlib`** (pure numpy/sklearn; DP classifiers + mechanisms; **s390x: yes**). AIM needs a few CPU minutes at small scale. Synth-MIA repo URL not linked on arXiv; find it on GitHub or hand-roll a shadow-model MIA.
- **Dataset:** UCI Adult, BAF, Diabetes 130-US hospitals.
- **Rubric fit:** C1 (share sensitive data safely), C2 (DP + attack-audit loop is above average), C3 (CPU-bound, fits LinuxONE).

### F2.4 Membership-inference auditing of our own model (RMIA)
- **Method:** **RMIA** (Zarifzadeh, Liu, Shokri, ICML 2024 oral): likelihood-ratio test using reference models + population samples; high power at very low FPR even with **1 reference model** → cheap enough for a hackathon. Show "before DP: attack AUC X; after DP-trained model: AUC ≈ 0.5."
- **Evidence:** ICML 2024 peer-reviewed + implemented in ML Privacy Meter (NUS) + used as the standard attack in 2025 audits → KEEP (extended to 2024).
- **Library:** `privacy-meter` (torch-based; test install) or hand-roll for sklearn/XGBoost models. **s390x: yes if hand-rolled.**
- **Rubric fit:** C3 (measurable privacy), C2.

### F2.5 PII detection/redaction before any LLM sees data
- **Evidence (2026 benchmarks):** REDACT leaderboard: Presidio recall 0.07 on highest-sensitivity entities, micro-F1 0.195 vs GLiNER 0.32 vs LLM detectors ~0.5–0.64. PIIBench: all 8 systems low (Presidio top at F1 0.139, mainly via regex for structured IDs). The "OpenAI Privacy Filter" eval (single author, arXiv 2608.02616) shows strong in-distribution numbers but collapse on non-Latin scripts and general NER. → KEEP the finding "**regex/NER redaction alone is not enough**; layer regex + small NER + policy." The specific leaderboard numbers are WEAK (new, self-reported).
- **Library:** Presidio (needs spaCy; compiled wheels on s390x are a risk), GLiNER (torch + HF weights; endianness test). Fallback: regex + `transformers` NER that loads cleanly.
- **Rubric fit:** C1, C3 (pre-LLM gate). Low novelty alone; good as a component.

### F2.6 Prompt-injection defence by architecture, not filters
- **Method:** **CaMeL** (Debenedetti et al., Google/DeepMind/ETH, arXiv 2503.18813): a privileged LLM writes a plan as code; a quarantined LLM only parses untrusted data; a custom interpreter tracks provenance and enforces policies. 67% AgentDojo tasks solved with provable security (author claim). **Design Patterns** paper (arXiv 2506.08837; Invariant, **IBM**, ETH, Google, Microsoft…): plan-then-execute, action-selector, etc. **Meta "Agents Rule of Two"** (Oct 2025): no session should combine untrusted input + sensitive data + external action without a human.
- **Why "by design":** **"The Attacker Moves Second"** (arXiv 2510.09023, OpenAI/Anthropic/GDM et al., Oct 2025) broke **12 recent defences at >90% ASR** that had reported near-zero. So detector/filter-only guardrails are refuted as a security guarantee (see DO NOT USE).
- **Library:** `google-research/camel-prompt-injection` (reference code; needs an LLM API, so a local Granite via llama.cpp would need adaptation). Rule-of-Two is a pure design constraint → trivially implementable.
- **Rubric fit:** C2 + C3 (secure AI assistant done right); C4 (red-team demo).

### F2.7 PQC migration + Cryptography Bill of Materials (CBOM)
- **What's current:** NIST **FIPS 203 (ML-KEM), 204 (ML-DSA), 205 (SLH-DSA)** final Aug 2024. **HQC** selected Mar 2025 as backup KEM (draft ~2026, final 2027). FIPS 206 (FN-DSA/Falcon) in draft. **CBOM** was created by IBM Research → **CycloneDX 1.6 (Apr 2024), now ECMA-424**; CycloneDX 1.7 (Oct 2025) added an algorithm-family registry. Eurocrypt 2026 workshop paper (Hess, IBM) covers CBOM practice and regulatory drivers (EU CRA, DORA).
- **Tools:** **PQCA CBOMkit** (IBM-donated to Linux Foundation): `sonar-cryptography` (Java/Python source scanning), `cbomkit-theia` (Go; container images/dirs), `cbomkit-action`. `liboqs` 0.13+ (mlkem-native default; **portable C path is the one s390x would use; big-endian not confirmed**).
- **AI angle for novelty:** use ML to *prioritise* the inventory (classify crypto assets by quantum risk × data-shelf-life, "harvest-now-decrypt-later" exposure). IBM z16/z17 are marketed as quantum-safe systems → strong IBM Z advocacy.
- **s390x:** cbomkit-theia (Go) should cross-compile; sonar-cryptography needs SonarQube (heavy). Python AST/regex crypto scanner emitting CycloneDX JSON is the 1-day version.
- **Rubric fit:** C3 + Best IBM Z Advocacy; C2 only if the ML-prioritisation layer is real.

### F2.8 Federated learning (Flower + XGBoost)
- **Evidence:** Flower is the de-facto open FL framework with a federated-XGBoost quickstart (HIGGS) and the hFedXGBoost baseline (25–700× less communication, author claim, 2023). No strong 2025 breakthrough found in this pass → **WEAK for novelty**, KEEP as tooling.
- **s390x:** `flwr` is pure Python + grpcio (grpcio is in the image) → plausible. Simulating 3–5 "hospitals" on one VM is easy, but **"federated on one box" weakens the story** unless paired with SE/HE.

---

## THEME 3 — Wildcard (light pass, standouts only)
- **W1. TerraMind (IBM + ESA Φ-lab + Jülich, ICCV 2025):** any-to-any generative Earth-observation foundation model. Author/partner claim +8% vs 12 models on PANGAEA. **TerraMind-1.0-tiny** and edge-sized versions (Oct 2025) on Hugging Face. Use cases: flood/wildfire/land-use mapping for community resilience. s390x: torch + HF weights → endianness test; tiny variant is CPU-feasible for inference on a few tiles. Strong IBM lineage. **WEAK-KEEP** (vendor-heavy evidence; ICCV acceptance is real).
- **W2. Granite TTM for sustainability forecasting:** same model as F1.5, applied to grid carbon intensity or building energy (e.g. carbon-aware scheduling of batch jobs on LinuxONE). Cheap, IBM-native, CPU.
- **W3. Granite Guardian HAP-38M for community-safety moderation:** 38M-param encoder, IBM claims 8× faster than its 125M sibling on CPU. Ideal NNPA/CPU candidate for real-time moderation of community forums or helplines. Evidence is vendor-only → WEAK.

---

## Ledger — KEEP / WEAK / DO NOT USE

### KEEP (corroborated)
| Source | Claim used | Corroboration |
|---|---|---|
| Gibbs & Candès, ACI (NeurIPS 2021; arXiv 2106.00170) [extended: foundation] | online coverage under shift | 2502.00818 (2025), 2511.04275 (2025) build on and confirm |
| Wu et al., Error-quantified CI (arXiv 2502.00818, 2025) | continuous-feedback online CI | ACI line; 2511.04275 |
| MAPIE v1 docs (2025) | library, Mondrian removed in v1 | PyPI + readthedocs |
| Hollmann et al., TabPFN (Nature 637, 2025) | strong ≤10k rows | TabArena 2506.16791 (independent, with subset caveat) |
| TabArena (arXiv 2506.16791) | ensembled GBT/RealMLP still top overall | the TabPFN-3 report disputes it; the living leaderboard is the arbiter |
| Ekambaram et al., TTM (NeurIPS 2024) | ~1M params, CPU, zero-shot | IBM model card + IBM tutorial |
| Altman et al., AMLworld (NeurIPS 2023 D&B) [extended] | IBM synthetic AML data with ground truth | used by Multi-GNN, MEGA-GNN |
| Egressy et al., Multi-GNN (AAAI 2024) [extended] | multigraph GNN for AML | MEGA-GNN 2412.00241 builds on and beats it |
| Jesus et al., BAF (NeurIPS 2022 D&B) [extended] | fraud data with temporal shift + bias | Feedzai GitHub + Kaggle |
| TGB 2.0 (NeurIPS 2024 D&B) | heuristics often rival temporal GNNs | consistent with AMLworld's GBT baselines |
| Zarifzadeh et al., RMIA (ICML 2024) [extended] | strong cheap MIA | ML Privacy Meter; widely used in 2025 audits |
| Stadler et al. (USENIX Sec 2022) [extended] | synthetic ≠ private | Synth-MIA 2509.18014 (2025) |
| Chen et al., DP tabular synthesis benchmark (arXiv 2504.14061) | no universal winner | 2026 fairness benchmark 2607.07471 |
| Debenedetti et al., CaMeL (arXiv 2503.18813) | design-level PI defence | Design Patterns 2506.08837; Meta Rule of Two; Willison |
| Nasr et al., The Attacker Moves Second (arXiv 2510.09023) | 12 defences broken >90% ASR | Willison commentary; consistent with CaMeL's motivation |
| Meeus et al., SoK LLM MIAs (SaTML 2025) | LLM-MIA results driven by distribution shift | Duan et al., "Do MIAs work on LLMs?" (COLM 2024) |
| Relearning attacks on unlearning (ICLR 2025, CMU) | unlearned LLM knowledge recoverable | prior recovery studies; 8-method eval (RMU/TAR more robust) |
| NIST HQC announcement (Mar 2025) + FIPS 203/204/205 | PQC standards state | multiple press + NIST page |
| CycloneDX 1.6/ECMA-424 + Hess (Eurocrypt 2026 workshop) | CBOM standard, IBM origin | CycloneDX release notes; IBM donation blog |
| ~~IBM HElayers s390x wheel~~ → moved to DO NOT USE (2026-10-16 PyPI check: x86_64 only) | — | — |
| IBM Secure Execution docs + FOSDEM/KVM Forum talks | confidential VMs on s390x | multiple IBM talks |
| SAMM (Feedzai, KDD-W 2019) [extended] + ROSFD (arXiv 2504.10229) | label-delay-aware drift monitoring | two independent groups |
| LLM-narrative faithfulness (2412.10220, 2512.00163, 2608.02412) | LLM explanations drift from SHAP | three independent papers agree |

### WEAK (thin, preprint-only, or vendor-only)
| Source | Why weak |
|---|---|
| Bary et al., conformal multi-expert deferral (arXiv 2509.12573) | preprint, image datasets only, no code |
| Singh et al., cost-sensitive CP benchmark (arXiv 2607.27143) | preprint, no code, datasets not named on the abstract page |
| Jun & Ohn retrospective online CI (arXiv 2511.04275) | single preprint |
| TabPFN-3 report (arXiv 2605.13986) | authors' own, H100-scale, license unclear |
| Spyre RAG on LinuxONE (arXiv 2608.21393) | single preprint, "early analysis" |
| IBM zDLC/AI Toolkit perf claims (3.5×, 2× INT8, 450B inferences/day) | vendor marketing; 3.5× footnote compares against an x86 setup |
| Granite Guardian HAP-38M speed claims | vendor-only |
| TerraMind PANGAEA +8% | IBM/ESA claims (ICCV acceptance is real) |
| REDACT / PIIBench / OPF PII numbers (2026) | new, self-reported leaderboards; OPF single-author |
| Synth-MIA (arXiv 2509.18014) | preprint (direction corroborated by Stadler) |
| Tab-PE (Microsoft, ICML 2026 listing) | not opened in full |
| dpmm library claims (2506.00322) | author benchmark |
| Drift benchmark 2606.07789 detector ranking | single new paper |
| Hong & Nasreddine, CP practical challenges (2510.10324) | theoretical, full-CP focused; irrelevant to split/online CP |
| Flower hFedXGBoost comms claims | 2023, author claim |

### DO NOT USE (refuted / hype) — quarantined
| Claim | Refuted by | Discredited metric |
|---|---|---|
| "Our prompt-injection classifier/guardrail makes the LLM secure" (filter-only defences) | Nasr et al. 2510.09023 (12 defences, >90% ASR under adaptive attack); CaMeL & Design-Patterns papers argue design-level isolation is required | near-zero ASR figures reported by the original defence papers |
| "MIAs show LLM X memorised dataset Y" from post-hoc member/non-member splits | Meeus et al. SaTML 2025; Duan et al. COLM 2024 (bag-of-words classifier separates the splits) | high LLM-MIA AUCs in those post-hoc benchmarks |
| "Synthetic data is anonymous / privacy-preserving by construction" (non-DP) | Stadler et al. USENIX Sec 2022; Synth-MIA 2025 (PATEGAN leaks; similarity metrics ≠ privacy) | DCR/"distance-to-closest-record" as proof of privacy |
| "Machine unlearning removed the data from the LLM" (as a compliance guarantee) | ICLR 2025 relearning attacks (benign fine-tuning restores knowledge); evaluation-metric critique | "forget-set accuracy ≈ 0" as evidence of deletion |
| "LLM explains the model's decision" (unchecked) | 2412.10220, 2512.00163, 2608.02412 | LLM narrative accepted as faithful without SHAP verification |
| "TabPFN beats GBDT everywhere" | TabArena (ensembled RealMLP/TabM/LightGBM top v0.1; TabPFN limited to subsets); practitioner reports on hidden-default sensitivity | blanket "SOTA on tabular" claims |
| "Concrete-ML / OpenFHE / TenSEAL will just pip-install on s390x" | no s390x wheels found; HElayers is the s390x-supported path | n/a (feasibility) |

---

| "pyhelayers has an s390x wheel" | PyPI 2026-10-16 lists only x86_64 wheels (1.5.5.1–1.5.5.4) | critic-feasibility.md |

## Community consensus (blended)
- **Prompt injection:** the practitioner consensus (Simon Willison's blog, which is the hub of HN discussion; Meta's Rule of Two; "lethal trifecta" widely repeated across security blogs) agrees with the research: **no filter is reliable; constrain the architecture and add a human in the loop for the risky combination.** Strong agreement; no credible contrary view found.
- **TabPFN:** practitioner write-ups (AI Horizon Forecast, PyCon DE 2026 talk, TDS) are enthusiastic but repeat the same caveats: hidden defaults matter, slowest model, non-commercial weights, GBT still wins on cost at scale. Consensus = **great for small data, not a GBT replacement**. Matches TabArena.
- **Conformal prediction:** practitioner framing (Angelopoulos & Bates tutorial, 2026 blogs, R-bloggers) = easy wrapper with a real guarantee. Recurring caveat: **marginal coverage hides minority-class failure** (matches the Mondrian evidence). No refutation found. Direct Reddit/HN threads did not surface in search (limitation of this pass).
- **Synthetic data:** the privacy community (Stadler talk, Synth-MIA, DP benchmarks) agrees that only DP plus an audit gives a defensible claim. Vendor marketing that says otherwise is the losing view.
- **IBM Z AI performance claims:** no independent community benchmarks found; treat all latency/throughput numbers as IBM claims and **measure our own on the VM**.

---

## Final call (research + community, aggregated)
**Theme 1 (recommended) — "Calibrated real-time decisions with an abstention budget":** XGBoost (or a small torch MLP pushed through `torch_nnpa` if NNPA exists) → **Mondrian + adaptive conformal** prediction sets → auto-act / **defer to analyst** (optionally conformal multi-expert routing) → label-delay-aware score-drift monitor that triggers ACI recalibration → Granite (llama.cpp) explanation **checked against XGBoost SHAP contributions** before display. Data: **BAF** (built-in temporal shift) or **IBM AMLworld** with graph features. Every component is pure Python or already in the image. Novelty sits in the combination: calibrated deferral under drift, plus a faithfulness-checked explanation, plus measured on-platform latency.

**Theme 2 (strong alternative) — "Score without seeing":** **HElayers CKKS** encrypted inference on s390x + **DP-trained model (diffprivlib)** + **RMIA audit** showing the leakage drop + Secure Execution as the deployment architecture (described, not claimed as run). Optional add-on: a CaMeL/Rule-of-Two-constrained Granite assistant over the results.

**Day-1 hour-1 smoke tests (both themes):** `grep nnpa /proc/cpuinfo`; `import torch_nnpa`; `pip install mapie crepes river diffprivlib`; `pip install pyhelayers` (check python==3.11); load one HF safetensors model and compare its output to a known x86 value (endianness).

### Source URLs (fetched/surfaced 2026-10-16)
- jupyter-lab-ml README + packages.txt: github.com/linuxone-community-cloud/jupyter-lab-ml
- ACI: arxiv.org/abs/2106.00170 · ECI: arxiv.org/abs/2502.00818 · Retro-online CI: arxiv.org/abs/2511.04275
- Cost-sensitive CP benchmark: arxiv.org/abs/2607.27143 · Conformal multi-expert deferral: arxiv.org/abs/2509.12573 · Conformal rejector: mlanthology.org/tmlr/2026/fang2026tmlr-learning
- MAPIE v1 notes: mapie.readthedocs.io/en/stable/v1_release_notes.html
- TabPFN Nature: pubmed.ncbi.nlm.nih.gov/39780007 · TabArena: arxiv.org/abs/2506.16791 · TabPFN-3: arxiv.org/abs/2605.13986 · caveats: aihorizonforecast.substack.com/p/tabular-foundation-models-are-not
- TTM: proceedings.neurips.cc (2024, 874a4d89…) · AMLworld: arxiv.org/abs/2306.16424 · Multi-GNN: arxiv.org/abs/2306.11586 · MEGA-GNN: arxiv.org/abs/2412.00241 · TGB 2.0: arxiv.org/abs/2406.09639 · BAF: github.com/feedzai/bank-account-fraud
- SAMM: arxiv.org/abs/1908.04240 · ROSFD: arxiv.org/abs/2504.10229 · drift benchmark: arxiv.org/abs/2606.07789
- LLM-XAI faithfulness: arxiv.org/abs/2412.10220 · arxiv.org/abs/2512.00163 · arxiv.org/abs/2608.02412
- zDLC 5.0: community.ibm.com (sunny-anand 2025/06/10) · AI Toolkit Redpaper: redbooks.ibm.com/abstracts/redp5749.html
- Secure Execution: ibm.com/docs/en/linuxonibm/lxsw/lxsw_confidential.html · Spyre RAG: arxiv.org/abs/2608.21393
- HElayers: developer.ibm.com/blogs/secure-ai-workloads-using-fully-homomorphic-encrypted-data · pypi.org/project/pyhelayers
- DP synth benchmark: arxiv.org/abs/2504.14061 · Synth-MIA: arxiv.org/abs/2509.18014 · Stadler: arxiv.org/abs/2011.07018 · dpmm: arxiv.org/abs/2506.00322
- RMIA: proceedings.mlr.press/v235/zarifzadeh24a.html · LLM-MIA SoK: arxiv.org/abs/2406.17975
- CaMeL: arxiv.org/abs/2503.18813 · Design patterns: arxiv.org/abs/2506.08837 · Attacker moves second: arxiv.org/abs/2510.09023 · Rule of Two: simonwillison.net/2025/Nov/2/new-prompt-injection-papers/
- Unlearning relearning: arxiv.org/abs/2406.13356
- PII: arxiv.org/abs/2604.15776 · arxiv.org/abs/2608.02616 · papers.cool/arxiv/2606.19881
- NIST HQC: nist.gov/news-events/news/2025/03/nist-selects-hqc-fifth-algorithm-post-quantum-encryption · CBOM: research.ibm.com (anatomy-of-CBOM, Eurocrypt 2026) · CBOMkit: github.com/cbomkit
- TerraMind: huggingface.co/ibm-esa-geospatial · Granite HAP: research.ibm.com/blog/efficient-llm-hap-detector · Flower XGBoost: flower.ai/docs/framework/tutorial-quickstart-xgboost.html


---

<!-- §4: _ledgers/winning-criteria.md -->

# § What wins (and loses), tuned to the IBM Z rubric
Research pass: 2026-10-16, for the IBM Z Datathon 2026 (Manchester hub, 4-person team, build Oct 17 9 AM to Oct 18 ~10 AM).
Rubric source: `../guidebook-digest.md`. Four criteria, 10 points each, plus the separate AI Innovation Excellence Award.

**Evidence quality, up front.** Peer-reviewed work on *how hackathon judges score* barely exists. The 2024–26 systematic
reviews (Frontiers in Education 2025/26, Cogent Education 2024, Springer EIT 2024) all say outcomes and judging are rarely
measured rigorously. So the "what wins" findings below rest on **practitioner judge write-ups from 2026** (several
independent ones that agree) plus older peer-reviewed work on continuation, creativity and judging bias. I extended
past 2 years only for the creativity science (Uzzi 2013, Acar 2019) and the Telum paper (ISCA 2022), since nothing newer
of that quality exists. Reddit could not be fetched directly (blocked). Community consensus comes from Hacker News
(Algolia API, ~120 comments scanned) and judge/winner blogs.

## CATEGORY INDEX
- §A What judges actually reward
- §B What loses
- §C The LLM-wrapper problem + anti-wrapper test
- §D Originality: generating and self-checking ideas
- §E Platform fit: making "why IBM Z" convincing
- §F Per-criterion scoring checklist (how to hit 9–10)
- §G The ≤3-minute video template
- §H 25-hour plan for 4 people
- §I Source ledger (KEEP / WEAK / DO NOT USE)
- §J Community consensus
- §K Final call

---

## §A What judges actually reward (KEEP, corroborated)

1. **A working end-to-end flow beats an ambitious deck.** Every 2026 judge write-up agrees (Kurbaitaev; JetBrains judges;
   Reskilll; Hsu/Browser Use). Reskilll's judge note-sheet puts "Does it work? (yes/no)" first. Show something working
   within ~90 seconds.
2. **One plain sentence that says what it is and who it's for.** "This is a tool that does X for Y." Judges carry
   that sentence into panel discussion. Pick the line you want a judge to repeat an hour later (Kurbaitaev; Beaulieu; Hsu).
3. **A named, specific user.** Not "hospitals" but "the triage nurse at a 40-bed A&E at 3 AM." It signals real
   research and answers "who would use this?" (Kurbaitaev; Hsu).
4. **Narrow scope, done well.** One thing built properly reads as good judgment. A "platform" in 25 hours reads as poor
   judgment (Kurbaitaev; JetBrains; Hsu).
5. **Problem framed with a number.** Open with one stat that shows the pain (Reskilll; Hsu "include numbers").
   This rubric scores *value to community* and *theme alignment* first, so this matters doubly here.
6. **Honesty about limits raises scores.** One judge saw named limitations *raise* marks (Kurbaitaev). Devfolio's
   2026 audit system docks marks when claims don't match code. Overclaiming is now actively checked.
7. **Explain why the AI component matters**, not just that it exists (Beaulieu; Devfolio docks "custom architecture"
   that is a single pretrained load).
8. **Judges calibrate.** In judged competitions, early entries get lower, cautious scores while judges are still
   calibrating (RIETI piano study 2026; Queen Elisabeth contest). You can't pick your slot in a video round, so the
   lever you control is **memorability**: a sharp one-liner and one striking moment.

What judges *don't* score much: framework choice, lines of code, elaborate UI. Clean UI helps. Elaborate UI makes judges
wonder where the backend effort went (Kurbaitaev; Reskilll).

**This datathon specifically:** judges are **IBM SMEs and managers**, and criterion 3 explicitly asks for LinuxONE
features plus AI/ML open source. So unlike a generic hackathon, technical depth *on the platform* is scored by experts.
Past winners fit a pattern: a specific social problem, public data fused in a new way, a model actually running on
LinuxONE (2025 URSI: road safety from infrastructure + crime data; Team Oasis: lake encroachment from satellite images,
CNN on L1CC in Docker; VIT: Farmer's Friend). Thin evidence (3 examples), but it is this exact contest.

## §B What loses
- **No working demo, or a demo that doesn't match the repo** (all judge sources; Devfolio flags it as a hard case).
- **Context before product.** Long setup means judges spend the demo catching up (Kurbaitaev).
- **Scope too big.** Unfinished core flow. Mock only the non-core parts (data feeds), never the core (Hsu).
- **Generic idea.** The rubric's own 0–3 band is "commonly available concepts". Fraud dashboard #500 lives there.
- **Tech showcase with no real user.** "Who uses this?" has no answer.
- **Weak data story.** The video *requires* "data supporting the problem". No dataset, no number, no chart = lost marks on
  criteria 1 and 4.
- **Overclaiming.** "Real-time", "secure", "privacy-preserving", "uses Telum AI" without evidence. IBM SMEs will know.
- **Bolted-on platform.** Code that would run identically on a laptop, with LinuxONE as just the host.
- **Spending demo time on the stack** instead of the product (Kurbaitaev).
- **Not submitting** or blowing the 3-minute limit (criterion 4 says "within time limit").

## §C The "LLM wrapper" problem

**Definition (community + judges agree):** a polished UI or prompt around a general LLM API call, where the model provider
supplies all the intelligence. HN's most repeated form: "just a wrapper around OpenAI API with a custom prompt." Devfolio's
2026 judging audit docks Originality (7 → 4 in their example) when a "custom architecture" turns out to be one pretrained
model call.

**Why it scores low here (2024–26):** (1) Novelty: anyone can rebuild it in an afternoon, which is the rubric's
"commonly available" band. (2) Technical: nothing to optimise on LinuxONE if the brain is a remote API. (3) Judges see
dozens per day; one judge estimates ~90% of entries now use AI, so a wrapper doesn't stand out.

**Caveat (refutation found):** wrappers *do* sometimes win at generic hackathons where slick UI wins the room (HN comment,
Feb 2026: "The winning project? A slick UI wrapped around a basic LLM API call"). This rubric is different: 20 of 40
points (Novelty + Technical/LinuxONE) plus the AI Innovation award all punish a wrapper. So: avoid.

### Anti-wrapper test (all six must pass)
1. **Delete-the-LLM test.** Remove every LLM call. Does the product still make its core decision / prediction / number?
   It must. The LLM may only make that output easier to use.
2. **Where does the value come from?** Name it in one line: our data pipeline (fused datasets nobody joined), our trained
   predictive model, or our system design (where/when inference runs). "A good prompt" is not an answer.
3. **Measured evaluation.** A metric on held-out data (F1/AUROC/recall at a fixed false-alarm rate, latency p95) versus a
   baseline, **including a "just ask the LLM" baseline**. If the LLM alone matches you, you are a wrapper.
4. **Afternoon test.** Could a competent student reproduce it with ChatGPT and one prompt in an afternoon? Must be no.
5. **Bounded LLM job.** The GenAI part has a narrow, grounded task, its inputs come from your model or data, and its
   output is checked (schema, guardrail, or citation back to the features).
6. **It runs on LinuxONE.** The predictive model trains or infers on the s390x VM. A remote API is not "AI on LinuxONE".

### Legitimate GenAI uses (the mandated Predictive + Generative lab means judges expect some)
- **Predictive decides, generative explains.** The predictive model (scikit-learn / XGBoost / small NN) makes the call.
  An LLM turns its top features (e.g. SHAP) into a plain-English rationale for the human decision-maker. This is the
  pattern IBM's own lab teaches.
- **Unstructured to structured.** The LLM extracts fields from free text (claims notes, reports) into features the
  predictive model uses. Evaluate extraction accuracy on a hand-labelled sample.
- **Privacy layer (Theme 2).** Redact or pseudonymise before anything leaves the box, or generate synthetic records for
  testing. Must be evaluated (re-identification check), or don't claim it.
- **Prefer a small open model running on the VM** (if it fits) over a remote API. It strengthens criterion 3 and the
  "data never leaves" story. If you must call a remote API, say so plainly and keep sensitive data out of it.

## §D Originality: generating and self-checking ideas

**Science behind it (extended past 2 years, nothing newer of this quality):**
- Uzzi et al. (Science 2013, 17.9M papers): highest-impact work is **mostly conventional with a small atypical
  combination**. Such work was about **2× as likely** to be a hit. Teams were 37.7% more likely than solo authors to
  make such combinations. Translation: a familiar, credible problem plus one unexpected ingredient. Not weird for its own sake.
- Acar, Tarakci & van Knippenberg (J. Management 2019): constraints shape creativity, and some constraint helps more
  than none. Use the platform and themes as deliberate constraints.

**Techniques (pick 2–3, 20 minutes, then converge):**
1. **Combine two unrelated datasets** that nobody has joined (URSI did infrastructure + crime). Ask "what decision
   becomes possible only when A meets B?"
2. **Invert the obvious.** Everyone detects fraud *against* the bank; detect harm *done to* the customer (e.g. scam
   victims sending money willingly). Everyone predicts failure; predict who is about to be *missed* by a service.
3. **Pick an overlooked user.** Not the analyst. The person on the receiving end: the carer, the volunteer dispatcher,
   the small charity, the person with low literacy.
4. **New interaction modality.** Where the AI meets the user is often the novel part (screen-aware, voice-first,
   SMS-only for low-connectivity users, an alert that arrives inside an existing workflow rather than a new dashboard).
   It must still pass the anti-wrapper test.
5. **Constraint-driven.** Start from what LinuxONE is uniquely good at (decide inside a transaction stream; never move
   sensitive data; crypto at speed) and ask "what 'AI for Good' problem *needs* exactly that?" This also wins criterion 3.
6. **Change the time-scale.** From batch report to in-the-moment decision (Theme 1), or from one-off to continuous.

**10-minute novelty self-check (do it before committing):**
- GitHub: search `"<core idea keywords>"` and sort by stars. Devpost: search the project gallery for the keywords. Google
  Scholar: `"<problem>" machine learning` in the last 2 years. Also check the 2025 Z Datathon winners above.
- Scoring: 0 close matches = great. Matches exist but none combine **your** data + **your** user + **LinuxONE** = fine,
  and say what's new in one line. A near-identical top Devpost project = pivot one axis (user, data, or modality).
- Rule 4 of the guidebook bans taking ideas from others. Your check doubles as proof you didn't.
- Write the novelty line: "Unlike X (which does A), we do B for C, using D." If you can't fill it, it's not novel yet.

## §E Platform fit: making "why IBM Z / LinuxONE" convincing

**What IBM SMEs care about (architectural claims, KEEP; vendor numbers, treat as marketing):**
- **Co-located inference.** Telum's on-chip AI accelerator sits on the processor next to the transaction data. Design
  goal: score *every* transaction inside its own latency budget, without shipping data to a separate AI server (ISCA 2022
  industry paper, "AI accelerator on IBM Telum processor": 22× lower latency than vector units on a bank fraud model;
  IBM LinuxONE AI page). IBM's "<1 ms, 5M inferences/s" figures are **extrapolated from internal tests**; the Hot Chips
  2021 latency figures were **simulation projections**. Never quote them as your result.
- **Security.** Hardware crypto on every core (CPACF), Crypto Express HSMs, IBM Secure Execution for Linux
  (confidential computing: even admins can't see the guest), quantum-safe algorithms (ML-KEM / ML-DSA).
- **Reliability and scale** for always-on, high-stakes workloads.
- **Data gravity.** The data is already on Z in banks, insurers, governments. The pitch is "bring the model to the data."

**How to make it convincing, not bolted on:**
1. **Make the platform a requirement of the problem.** Theme 1: "the decision has to happen inside the event stream,
   so inference is co-located with the data." Theme 2: "the data may never leave the trusted box, so model and data
   live together, encrypted at rest and in transit."
2. **Measure on the VM.** Show your own numbers from L1CC: inference latency p50/p95, throughput, with a
   CPU-vs-accelerator or single vs. batched comparison. Real small numbers beat borrowed big ones.
3. **Check the hardware on day one (open question).** I could not confirm what hardware generation the Community Cloud
   VMs run on, or whether guests can use the AI accelerator. Run `uname -m` (expect `s390x`), `lscpu`, and
   `grep -o nnpa /proc/cpuinfo`. If `nnpa` shows, use IBM Z Accelerated TensorFlow / ONNX-MLIR (zDLC) / Snap ML and
   show the speed-up. If not, **don't claim Telum acceleration**. Talk about the production path instead
   ("on a z16/z17 this same ONNX model would run on the on-chip accelerator").
4. **Use crypto you can show.** `cat /proc/crypto`, `icainfo` (libica) or `openssl speed -evp aes-256-gcm` to show hardware
   AES. Encrypt the stored data and model artefacts. Screenshot it (the guidebook asks for security/scalability/compute screenshots).
5. **Containerise.** Docker/Podman on s390x, `docker ps` screenshot. Team Oasis (a winner) did exactly this.
6. **Big-endian gotcha.** s390x is big-endian. Team Oasis got wrong results until they used s390x-appropriate PyTorch
   builds. Prefer the provided Jupyter Lab ML image and IBM-built wheels; test model loading early.
7. **Speak their vocabulary correctly** (s390x, LinuxONE, Telum, zDNN, Secure Execution, CPACF). Misuse costs credibility.
   There is a separate **Best IBM Z Advocacy** award, so a clear "why Z" story has extra upside.

Sponsor-tech judging in general: at most hackathons "use of sponsor tech" is a gate (must use it) and "best use of X"
prizes reward depth over mentions (MLH sponsorship guide; FutureStack rules). Here it's 10 of 40 points plus an award.

## §F Per-criterion checklist: how to hit 9–10

**1. Value to community + theme (10)**
- [ ] Named user + one-sentence pain + one hard number from a credible source (ONS, NHS, WHO, peer-reviewed).
- [ ] Theme named out loud and the *mechanism* matches it (T1: real-time decision; T2: protected data; T3: genuinely novel).
- [ ] "What changes for the user": time saved, harm avoided, people reached, as a number estimate with the assumption shown.
- [ ] One responsible-AI line: bias check, human-in-the-loop, or what happens when the model is wrong.

**2. Novelty & originality (10)**
- [ ] Passes the anti-wrapper test (§C).
- [ ] Novelty line filled: "Unlike X, we do B for C using D."
- [ ] Self-check done (§D), with nothing near-identical.
- [ ] At least one genuinely unusual ingredient: data fusion, inversion, overlooked user, or modality.

**3. Technical design + LinuxONE + open-source AI/ML (10)**
- [ ] Architecture diagram: data in → pipeline → predictive model → (GenAI explain) → user, with LinuxONE boundary drawn.
- [ ] Predictive model trained/served on s390x. Eval metric vs. a baseline on held-out data.
- [ ] Hybrid / multi-model element (mirrors the mandated labs).
- [ ] Measured LinuxONE numbers (latency/throughput) + security (encryption) + container screenshots.
- [ ] Every open-source library linked in the README (Rule 5).

**4. Execution & pitch (10)**
- [ ] Video ≤ 3:00 (aim 2:50), all five required elements, visible LinuxONE instance and model.
- [ ] Working demo, one flow, real output. Every team member appears or speaks ("orchestrated team video").
- [ ] Repo: README with one-liner, diagram, how to run, results table, limitations. Title `[Team Name_IBM Z Datathon 2026 Project]`.
- [ ] Captions on (judges may watch muted), readable fonts, no dead air.

**AI Innovation Excellence Award (+20):** needs high Novelty *and* Technical. Show measurable impact, a path to scale on
LinuxONE, and one unconventional AI idea that is clearly yours.

## §G The ≤3-minute video template (target 2:50)

| Time | Section | What's on screen | Covers |
|---|---|---|---|
| 0:00–0:15 | **Hook** | Named user + the one stat. Say the one-liner. | Problem |
| 0:15–0:35 | **Data behind the problem** | 1 chart from your data, dataset names on screen. | Data |
| 0:35–1:35 | **Demo** (longest part) | Real flow: input arrives → model decides → user sees result + explanation. One "wow" moment. | Solution |
| 1:35–2:20 | **IBM Z** | 10s architecture diagram, then screen capture of the LinuxONE terminal: `uname -m` = s390x, model loading, live inference with timing, encryption/container proof. | IBM Z, instance, model |
| 2:20–2:40 | **Proof + impact** | Eval metric vs. baseline, latency number, impact estimate, one limitation. | Credibility |
| 2:40–2:50 | **Close** | One-liner again, team names, repo link. Stop. | Memorability |

Production rules: script it word-for-word (~380 words at ~140 wpm for 2:45 of speech). Record screen segments separately,
then narrate. Burn in captions. Start with the product, not team intros (Reskilll; hackathon.com tips; Kurbaitaev). Lead
with the product and keep slides to the diagram and one chart. Record a first rough cut by the early hours so the
final cut is editing, not building. Short, informal, talking-plus-screen video holds attention better than polished
lecture style (Guo et al. 2014, about lecture video, so weak support).

## §H 25-hour plan for 4 people

**Roles (fixed by 10:30 on Day 1):**
- **P1 Data/ML lead**: dataset pipeline, feature engineering, predictive model, eval vs. baseline.
- **P2 Platform lead**: LinuxONE VM, environment, container, s390x quirks, crypto, latency benchmarks, screenshots.
- **P3 App/GenAI lead**: demo UI (thin), API around the model, the bounded GenAI explanation layer.
- **P4 Story/product lead**: problem stats, user framing, novelty check, README, diagram, video script and edit. Also tests the demo as a user.

**Day 1, in person (Manchester)**
| Time | Milestone |
|---|---|
| 08:00–10:00 | Arrive, kick-off. P2 logs into the VM and runs the hardware check (§E.3) **during** kick-off. |
| 10:00–10:45 | **Idea lock.** Run §D techniques (20 min), 10-min novelty check, anti-wrapper test, write one-liner + novelty line. Commit. |
| 10:45–13:00 | Data in and cleaned (P1). Env + container + "hello model" on s390x (P2). UI skeleton (P3). Stats + diagram v1 (P4). |
| 13:00–14:00 | Lunch. **Checkpoint 1:** does a dummy model run on LinuxONE end to end? If not, fix that first. |
| 14:00–17:00 | Baseline model trained + evaluated. Thin end-to-end path: data → model → UI, even if ugly. **Checkpoint 2 at 16:30: the walking skeleton works.** Ask IBM SMEs in person anything platform-related now (best access you'll get). |

**Overnight, remote**
| Time | Milestone |
|---|---|
| 17:00–18:00 | Travel/food. Short call: what's done, what's cut. |
| 18:00–22:00 | Improve model, add GenAI explanation, benchmarks + security proof, screenshots. P4 writes the video script v1. |
| **22:00** | **Feature freeze.** Nothing new after this. Only fixes and polish. |
| 22:00–00:30 | Record demo and terminal segments. P4 rough-cuts the video. README draft. |
| 00:30–05:30 | **Shift sleep**: two sleep while two finish (swap at ~03:00). Never everyone asleep with the video unfinished. |
| 05:30–08:00 | Final video cut, voice-over, captions, check ≤3:00. Repo cleanup, links to every open-source resource. |
| 08:00–09:00 | Fresh-eyes review by the whole team against the §F checklist. Upload video. |
| **09:00–09:30** | **Submit** (30+ min before the ~10:00 deadline; uploads fail). |

Rules: keep `main` always demo-able, risky work on branches (Hsu). Mock only non-core data feeds. If the model is weak,
ship it honestly with its metric and a clear limitation. Don't hide it.

---

## §I Source ledger

### KEEP (corroborated)
| Source | Used for | Corroborated by |
|---|---|---|
| Kurbaitaev, "What Judges Actually Score", DEV, Jul 2026 (judge, 1 yr of events) | Working demo > slides; one-liner; narrow scope; named user; admitting limits; skip stack talk | JetBrains judges 2026; Reskilll 2026; Hsu 2026; HN |
| Hsu (Browser Use, YC W25), "How to Win Hackathons", Feb 2026 (multi-time winner) | Real problem + named user; end-to-end POC; mock non-core only; one flow; main always working | Kurbaitaev; Reskilll |
| Reskilll, "Demo & Pitch Tips: 3 Minutes", 2026 | 3-min structure + time split; "Does it work?" first | Hsu; hackathon.com video tips; Kurbaitaev |
| Devfolio, "The Discerning Machine", May 2026 | Wrapper docked on Originality; claims vs. code checked; overclaiming penalised | HN wrapper threads; Beaulieu |
| HN comments via Algolia (~120 comments, 2012–2026) | Wrapper definition; demo/presentation dominance; judges vary | Judge blogs above |
| Uzzi et al., *Science* 342 (2013) | Conventional + atypical combination ≈ 2× hit rate; teams 37.7% more likely to combine | "Deep Learning in Science" review (arXiv 2009.01575) restates it. Extended past 2 yrs: foundational. |
| "AI accelerator on IBM Telum processor", ISCA 2022 industry track (ACM DOI 10.1145/3470496.3533042) | On-chip, coherent accelerator for in-transaction inference; 22× latency vs vector units on fraud model | IBM LinuxONE AI page; IBM Telum announcement; Hot Chips 33 slides |
| IBM LinuxONE security page + Redbook REDP-5535 + IBM community posts | CPACF, Crypto Express, Secure Execution, quantum-safe | Each other (all IBM, so architectural facts only) |
| IBM community blog, Team Oasis (winners), Apr 2025 | L1CC + Docker + CNN; big-endian PyTorch gotcha | IBM s390x docs on ONNX/zDLC (endianness is why IBM ships s390x builds) |

### WEAK (thin support, not fully fetched, or tangential)
| Source | Why weak |
|---|---|
| JetBrains AI blog, "Notes from the judging table", Jun 2026 | 403 on fetch; content seen only via search snippets ("confusing demo loses to simpler one", show something in ~90s). Agrees with KEEP set. |
| Beaulieu, "What AI hackathon winners have in common", DEV, Jul 2026 | Reasoning from 6 named winners, no data. "Explain why the AI matters", "weakest variable caps score". |
| Nolte, Chounta & Herbsleb, "What happens to all these hackathon projects?", PACM HCI (CSCW) 2020 | Fetch refused; abstract via search. About continuation, not judging. Winning linked to technical preparation and number of technologies. Older. |
| Univ. of Tartu thesis (2019, Nolte supervisor), Devpost ~60k projects | Fetch refused; findings not visible. |
| Affia-Jomants, Gama, Herbsleb & Nolte, hackathon planning kit, arXiv 2008.08025 (v3 Mar 2025) | Organiser-side; abstract only. Supports "publish criteria, pitch + demo" format. |
| Acar, Tarakci & van Knippenberg, *J. Management* 45(1) 2019 | Abstract only read; "some constraint helps" from the authors' HBR companion summary. Old. |
| RIETI piano-competition order-effect study (2026) + Queen Elisabeth contest study | Not hackathons. Supports "judges calibrate, early entries score lower". |
| Guo, Kim & Rubin, L@S 2014 (6.9M edX sessions) | Lecture video, not pitches. Shorter, informal video = more engagement. |
| Eugene Yan, "How to Win a Data Hackathon" (Hacklytics 2021) | Single event, older. Data-hackathon rubric weights visualisation; winners deployed prototypes. |
| Systematic reviews: Frontiers in Education 2025/26 (37 studies), Cogent Education 2024, Springer EIT 2024 | Used only to show the gap: judging outcomes rarely measured. |
| Past Z Datathon winners (URSI 2025; Oasis; VIT Farmer's Friend) | 3 examples, no judge feedback published. Pattern only. |

### DO NOT USE (refuted or unverifiable; metrics stripped)
| Claim | Source | Why quarantined |
|---|---|---|
| "MLH research shows judging criteria drive most outcome variance"; "winners decided in the first 2 hours" | HackerEarth blog | Unverifiable; page carried text aimed at AI summarisers; weights labelled "illustrative". |
| "80–95% of AI wrappers fail / 3–5% reach $10k MRR" | Wrapper-moat blogs (2026) | No primary source. Not needed anyway. |
| "Wrappers never win hackathons" | Folk wisdom | Refuted: HN Feb 2026 reports a slick-UI wrapper winning. Keep only the narrower claim: wrappers lose on Novelty/Technical-heavy rubrics like this one. |
| "<1 ms / 5M inferences per second" as *our* result | IBM marketing | Extrapolated from internal tests (IBM footnotes); Hot Chips latencies were simulations. Not our VM. Quote only as IBM's production claim, labelled. |
| "Polish/visual design wins" (as a rule) | HN 2012; Hsu | Contradicted by Kurbaitaev (elaborate UI adds little) and Reskilll (UX intuitive, not fancy). Resolved: clean and clear, not elaborate. |

## §J Community consensus (HN + winner/judge blogs; Reddit not reachable)
- **Strongest, most repeated:** demo/presentation decides more than code depth ("only the demo is judged", 2026; "make
  sure your presentation is flawless", 2012). Agrees with every judge blog.
- **Repeated:** judges reward real-world usefulness and plausible impact over clever hacks (~6 HN comments).
- **Repeated:** "just a wrapper" is a common put-down (~10 HN comments). What makes something more than a wrapper:
  own data/memory layer, cost/context engineering, own model, workflow integration.
- **Contrasting view:** "everything is a wrapper", so the label is lazy (~5 comments). Winner here: the label still
  matters when the rubric scores originality and platform depth, as this one does.
- **Repeated:** novelty/hardware/unusual modality stands out ("hardware wins big"; "judges swept away by fancy AR").
- **Minority:** mock-data dashboards sometimes win and annoy people. A reason to show real data on LinuxONE.

## §K Final call (professional + community, aggregated)
Professional and community evidence agree on the core. **Win with a narrow, real, working end-to-end flow for a named
user, with a numbers-backed problem, an honest eval, and a clear one-liner.** For *this* rubric, add two things a
generic hackathon doesn't weigh: (1) the **core intelligence must be your own predictive model and data fusion running
on LinuxONE**, with GenAI as a bounded explainer, never the product; (2) **"why Z" has to be a requirement of the
problem** (co-located, in-the-moment decisions or data that can't leave), proved with your own measured screenshots,
never borrowed IBM numbers. Novelty comes from a familiar, credible problem plus one atypical ingredient (Uzzi), checked
against GitHub/Devpost in 10 minutes. Freeze features at 22:00, have a rough video cut by 00:30, submit by 09:30.


---

<!-- §5: _ledgers/judge-prosecutor.md -->

# § Judge-prosecutor: past IBM Z Datathon winners vs. the 2026 rubric
Written 2026-10-16. Role: a harsh IBM Z SME on the 2026 panel, testing whether past winners would survive this year's rubric.
Evidence: `past-winners.md` (repo and gallery facts, evidence grades) + `../guidebook-digest.md` (rubric) + `winning-criteria.md` (anti-wrapper test).
No new fetches were made, so every score rests on the ledger's recorded evidence. Where the ledger says "?", I score as if there is **no evidence**. That is how a 2026 judge reads a submission: if it isn't shown, it didn't happen.
**Rule 4 reminder:** this file is a list of failure patterns. None of these ideas may be reused.

## CATEGORY INDEX
- §A Scoring lens (how strict, and why)
- §B Per-project prosecution (scores, fatal flaws, 2026 verdict)
- §C Score table
- §D The 5 most common failure patterns
- §E What a 2026 team must do that none of them did
- §F Agentic closed-loop upgrades (which winners one would have elevated)

---

## §A Scoring lens
- **C1 Value/theme (10):** a critical need, a named user, and a mechanism that fits one of the 2026 tracks (Real-Time / AI Secured / Wildcard). A generic "helps people" framing caps at 6.
- **C2 Novelty (10):** 0–3 = "commonly available" (a Kaggle-tutorial task, or a project that already exists on GitHub 100×). It needs an atypical ingredient: data fusion, an inverted framing, an overlooked user, or a new modality.
- **C3 Technical + LinuxONE + OSS AI/ML (10):** I use the ledger's L1-depth scale. Depth 0 caps at 2, depth 1 at 4, depth 2 at 6. 7+ needs containers, crypto or scale **shown with screenshots**, plus a measured number. Claims without evidence score **negative** in spirit: they cost credibility on C3 and C4.
- **C4 Execution/pitch (10):** working demo, the five required video elements, LinuxONE instance and model on screen, repo alive and honest.
- **AI-I (AI originality, /10)** and **AI-T (transformational impact + technical excellence on LinuxONE, /10)**: the two AI Innovation Excellence Award criteria. The award is only reachable at roughly 8+ on both.

---

## §B Per-project prosecution

### 2025: Life Aspirant's, Plastic detection in water (Global 1st, grade B)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 7: a real harm, but no named user (who acts on a detection?) | 3: plastic detection from imagery is a common Kaggle/remote-sensing task | 2: no L1 evidence in the repo | 6: the pitch carried it, but 4 files and claimed-not-shown metrics | 2 | 2 |
**Fatal flaws:** the 89%/95%/40% metrics are unsourced (the ledger marks them DO NOT USE). The IoT buoys and drones are concept-ware. One notebook plus an index.html. Zero LinuxONE proof. "Detect, track, forecast" is three products claimed and not one shown.
**2026 verdict:** no. The C3 floor of 2 and IBM SMEs checking claims against the repo would sink it, and in a 2026 field it would not make a hub podium.

### 2025: Hackasaurs, Public-meal demand forecasting (Global 2nd, grade B)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 7: food waste in public programmes is a clear social good | 4: demand forecasting is textbook; the public-meal user is the only twist | 4: one "#CodingInLinuxOne" screenshot, nothing on containers, crypto or scale | 7: 9 dashboards, React frontend, R² reported | 3 | 4 |
**Fatal flaws:** **a data/user mismatch**. Walmart retail sales are standing in for public meal programmes, so the model never saw the target domain. The data is "synthetically enriched", which can hide how weak the signal really is. Three model families (LightGBM/XGB/LSTM) and 70+ features is breadth, not insight. Nine dashboards is scope creep. The ₹700-crore impact number is not tied to what the model actually prevents.
**2026 verdict:** borderline hub podium, not global. It is the most "complete" entry, but it would lose C3 to any team that shows a container plus a measured latency on s390x.

### 2025: Gradient Ascent, OcuGuard retinal triage (Global 3rd, grade B−)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 7: preventable blindness with a triage framing | 3: fundus multi-label classification is a classic Kaggle dataset task (APTOS/ODIR genre) | 2: no LinuxONE evidence recorded | 5: the triage-plus-advisory-report story is good, but the **repo is 404 now** | 2 | 2 |
**Fatal flaws:** commodity CNN on a public benchmark. No clinical validation or calibration story, yet it gives "Urgent" advice, which is a safety overclaim. The dead repo means no verifiability. Nothing about the idea needs Z.
**2026 verdict:** no. "Commonly available" on C2, with no platform depth.

### 2025: Tech Titans, TradeSentinel (Chennai 1st, grade B)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 5: protects retail traders, but market-abuse surveillance is the regulator's and the exchange's job, so the user is fuzzy | 5: collusion graph plus behavioural biometrics is a somewhat unusual combination | 1: the abstract **admits** "we have not used IBM features since they are not free" | 6: slick Next.js/Genkit build | 4 | 2 |
**Fatal flaws:** **the worst platform overclaim in the set**. It markets a "Crypto-Express-inspired" HMAC seal while admitting no IBM use, and an IBM SME will treat that as misrepresentation. It runs on simulated data. The buzzword stack (graph-ML + transformer ensemble + biometrics + LLM agent + ledger) is too much to be real in 24 h. The LLM agent layer is bolted on.
**2026 verdict:** no. C3 ≈ 1, and the admission alone disqualifies it from the AI award.

### 2025: BIG IRON, Heart-MRI classifier (Chennai 2nd, grade A)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 6: "second opinion" for clinicians, but there is no named workflow or user | 2: a CNN on cardiac MRI is a commonly available concept | 2: IBM Cloud COS + Db2, which is **IBM but not LinuxONE** | 5: working Flask app plus XAI heatmaps | 2 | 2 |
**Fatal flaws:** it confuses "IBM brand" with "IBM Z". No s390x, no L1CC. The diagnostic claim has no validation set provenance or clinical caveat. The heatmaps are the only differentiator.
**2026 verdict:** no.

### 2025: YuktiX, Fog/weather anomaly map (Bangalore 2nd, grade B)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 4: road fog safety is real, but no user or decision is defined | 3: RF + IsolationForest on weather is tutorial-level | 2: notebook-level at best | 3: 5 files, boilerplate README | 1 | 1 |
**Fatal flaws:** **fully synthetic data for 5,000 locations**. The model learns the generator, so its accuracy is meaningless. There is no real user and no ground truth. The heatmap does all the work.
**2026 verdict:** no. It only shows how shallow some hubs were.

### 2025: Medikate, Missed-dose risk (London 1st, grade B), the strongest of the set
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 7: medication non-adherence is a large, under-served harm; a "privacy-safe" angle fits Theme 2 | 6: predicting *adherence* rather than diagnosis is a smart inversion | 5: FastAPI **served on LinuxONE** (depth 2), Tabular Transformer, imbalance handling | 6: React dashboard with CSV upload works end to end | 4 | 4 |
**Fatal flaws:** the README **claims Confidential Computing / OpenShift with no evidence they were built**. That is exactly the claim a 2026 IBM SME will probe, and it would drag C3 down to about 4 and hurt C4 trust. "Privacy-safe" is asserted, not tested (no re-identification check, no encryption shown). MEDDATA.csv provenance is unclear. There is no intervention: it predicts a miss, then nothing happens.
**2026 verdict:** a plausible hub podium if the overclaims are removed. Not global without real Secure Execution or crypto evidence and a closed-loop action.

### 2025: AlphaPeterGamma, CrisisLens riot early warning (London 2nd, grade A)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 7: early warning for communal violence, a clear Theme 1 fit | 6: BERTweet embeddings → influence graph → attention GNN is the most technically original pipeline in the set | 4: all code written in L1 Jupyter (depth 1–2); no container, crypto or latency | 6: crisis heatmaps, a clear story | 5 | 4 |
**Fatal flaws:** **responsible-AI exposure**. Monitoring public discourse to predict "riots" sits close to Rule 7 (political) and to surveillance concerns, and it gives no account of false positives or misuse (who gets policed?). It used historical cleaned datasets, so "early warning" was never run on a live stream. It has no lead-time evaluation (how many hours before the event?). Jupyter-only means nothing is deployable.
**2026 verdict:** possible hub podium. A 2026 panel would ask hard ethics questions, and C3 leaves points on the table.

### 2025: IBMGER004, Interstate conflict early warning (Germany 1st, grade B)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 6: conflict prevention matters, but the user (a diplomat? an NGO?) is undefined | 5: the trade-interdependence → conflict fusion (UCDP+UN+IMF) is a decent atypical join | 3: "train our models on IBM Z"; simple NN → LSTM | 4: GitLab repo, no visible demo artefact recorded | 3 | 2 |
**Fatal flaws:** annual macro data cannot support "early warning" at a useful granularity. An LSTM on a few dozen yearly steps per dyad is overfitting bait. There are no baselines against established conflict-forecasting work (ViEWS, for example). It is geopolitically sensitive.
**2026 verdict:** no. A nice data fusion with weak modelling and no platform depth.

### 2025: AnalytIQ, URSI road-safety index (South Africa 1st, grade A, the guidebook's showcase)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 7: women and night commuters, a clear "who benefits" | 4: crime + infrastructure fusion; but safety routing is crowded (HaloMap, SurakshaMap and weWalk all exist, and none of them placed) | 1: **IBM Watson Studio, not LinuxONE**; `src/*.py` files are **empty** | 6: a strong map "wow factor" | 2 | 2 |
**Fatal flaws:** the code is a facade (empty source files). A weighted score or logistic regression with no ground-truth evaluation means "Risky" is the authors' opinion, encoded. Quarterly precinct-level crime is too coarse for road-level labels. There is no LinuxONE at all. It also carries a stigmatisation risk (labelling neighbourhoods "risky").
**2026 verdict:** no. It won 2025 on story and visuals. Under the 2026 C3 and screenshot requirement, it collapses.

### 2025: Izimpisi ze-Data, Health-fund misallocation (South Africa 2nd, grade B−)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 7: public-health corruption is a critical harm | 4: anomaly detection on spending is common | 1: "IBM Z and LinuxONE" claimed; no evidence; repo 404 | 4 | 2 | 1 |
**Fatal flaws:** **synthetic data with injected anomalies**, so the detector finds what the authors planted. The repo is dead. The platform claim is unverified.
**2026 verdict:** no.

### 2023: CodeCatalysts, Hate-speech BERT moderator (2nd, grade A)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 5: moderation matters; no specific community or user | 2: fine-tuning BERT on Kaggle tweets is the canonical "commonly available" NLP project | 6: **real s390x Docker deploy on L1CC, a big-endian weight fix, <1 s inference**, the best platform work of any winner | 5 | 2 | 4 |
**Fatal flaws:** a 95% accuracy figure on an imbalanced dataset with no per-class or bias analysis, which is exactly where hate-speech models fail (dialect bias). The REST API was added *after* the event. The concept is a tutorial.
**2026 verdict:** no on totals, but it is **the template for C3**. Copy its platform discipline, not its idea.

### 2023: Uncalled coders, Transaction fraud (2nd, grade B)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 3 | 1: "fraud dashboard #500" | 2 | 3: one notebook, template README | 1 | 1 |
**Fatal flaws:** generic in every dimension. Ironically, fraud is the one domain where Z's in-transaction inference story is strongest, and they didn't use it.
**2026 verdict:** no.

### 2021: Fantastic Four, Farmer's Friend crop recommendation (3rd, grade B)
| C1 | C2 | C3 | C4 | AI-I | AI-T |
|---|---|---|---|---|---|
| 5: farmer livelihoods, but no channel to reach farmers | 1: the Kaggle crop-recommendation dataset is one of the most-cloned beginner projects | 2: notebook on Z | 3 | 1 | 1 |
**Fatal flaws:** **99% decision-tree accuracy** is a red flag for a trivially separable or leaky merged dataset, not a real result. It has no user pathway.
**2026 verdict:** no.

### Grade-C entries (grouped, not scored)
Data Detectives (London 2023), Carmex – Lambda Prime, RIP_ENGINEERS, Ctrl Alt Del, The Code Wizards, Data_R_Us, Starfall stallions, the Imperial tweet→charity classifier, the Jason Li NN, RUNTIME TERRORS (Bangalore 1st, ambiguous which project), and Team Oasis. There isn't enough evidence to prosecute them. A shared signal: where any detail exists (the charity classifier, Oasis), the platform use is depth 1–2. Oasis (a CNN in Docker on L1CC) and the charity classifier's LLM-labelling + XGBoost hybrid are the only C-grade hints that point *toward* the 2026 bar.

---

## §C Score table (2026 rubric, /40 + AI award criteria /20)
| Project | C1 | C2 | C3 | C4 | **Total /40** | AI-I+AI-T /20 | Place in 2026? |
|---|---|---|---|---|---|---|---|
| Medikate (London 1st '25) | 7 | 6 | 5 | 6 | **24** | 8 | Hub podium possible, if the overclaims are cut |
| CrisisLens (London 2nd '25) | 7 | 6 | 4 | 6 | **23** | 9 | Hub podium possible, but faces ethics questions |
| Hackasaurs (Global 2nd '25) | 7 | 4 | 4 | 7 | **22** | 7 | Borderline hub |
| Life Aspirant's (Global 1st '25) | 7 | 3 | 2 | 6 | **18** | 4 | No |
| IBMGER004 (Germany 1st '25) | 6 | 5 | 3 | 4 | **18** | 5 | No |
| URSI (SA 1st '25) | 7 | 4 | 1 | 6 | **18** | 4 | No |
| CodeCatalysts ('23 2nd) | 5 | 2 | 6 | 5 | **18** | 6 | No (but the C3 template) |
| OcuGuard (Global 3rd '25) | 7 | 3 | 2 | 5 | **17** | 4 | No |
| TradeSentinel (Chennai 1st '25) | 5 | 5 | 1 | 6 | **17** | 6 | No |
| Izimpisi (SA 2nd '25) | 7 | 4 | 1 | 4 | **16** | 3 | No |
| BIG IRON (Chennai 2nd '25) | 6 | 2 | 2 | 5 | **15** | 4 | No |
| YuktiX (Bangalore 2nd '25) | 4 | 3 | 2 | 3 | **12** | 2 | No |
| Farmer's Friend ('21 3rd) | 5 | 1 | 2 | 3 | **11** | 2 | No |
| Uncalled coders ('23 2nd) | 3 | 1 | 2 | 3 | **9** | 2 | No |

**Read-across:** the best past winner scores 24/40 under strict 2026 reading. **No one clears 6 on C3**, and no one gets near the AI award (it needs about 16+/20). C1 is uniformly fine (6–7), so value framing is table stakes, not a differentiator. The gap that's actually open is C3 + C2.

---

## §D The 5 most common failure patterns
1. **Fake or shallow LinuxONE ("IBM-branded ≠ IBM Z").** 10 of 14 sit at L1 depth 0–1. Watson Studio, IBM Cloud COS/Db2 or "not free" admissions get passed off as Z use. No winner shows containers + crypto + a measured number together. Under 2026's screenshot requirement, this is the single biggest point leak.
2. **Platform and metric overclaims.** Confidential Computing / OpenShift (Medikate), "Crypto-Express-inspired" (TradeSentinel), unsourced 89/95/40% (Life Aspirant's), 95–99% accuracies with no per-class or leakage check (CodeCatalysts, Farmer's Friend). IBM SMEs check claims against code, and in 2026 that turns a bonus into a penalty.
3. **"Commonly available" model on a benchmark dataset.** Kaggle fundus, cardiac MRI, hate-speech tweets, crop recommendation, transaction fraud, plastic imagery: a standard CNN/BERT/RF on a standard dataset. C2 sits at 1–3.
4. **Synthetic or mismatched data hiding weakness, with no honest evaluation.** Fully synthetic (YuktiX, Izimpisi), synthetically enriched or proxy data (Hackasaurs' Walmart → public meals), opinion-encoded labels (URSI). Almost nobody reports a baseline, a held-out metric that means something, or a failure analysis.
5. **Detect-and-display, no decision and no named user.** Nearly every winner ends at a heatmap or dashboard: no named operator, no action taken, no feedback on whether the action worked. Also thin or dead repos (2 are 404, URSI's source files are empty). "Real-time" or "early warning" is claimed on historical batch data.

---

## §E What a 2026 team must do that none of them did
1. **Run the model *in a container on the s390x VM* and screenshot it.** `uname -m` = s390x, `podman/docker ps`, the model loading, live inference. Nobody did containers + inference + screenshots together.
2. **Show measured platform numbers.** p50/p95 inference latency and throughput on the VM, and if possible a batched-vs-single or CPU-vs-NNPA comparison (check `grep nnpa /proc/cpuinfo` first; never borrow IBM's marketing figures).
3. **Make security real, not claimed.** Hardware AES via CPACF (`icainfo`, `openssl speed`), data and model encrypted at rest, a TLS endpoint. Claim Secure Execution only if it is truly available. Zero unbuilt claims.
4. **An honest eval with baselines.** A held-out metric vs. a trivial baseline **and** a "just ask the LLM" baseline. Per-class or subgroup errors. A stated limitation on screen.
5. **Real data (or disclosed synthetic data, used only for non-core feeds) that matches the target user.** No Walmart-for-public-meals proxies, and no learning from your own generator.
6. **A named operator and a decision.** "The pharmacist at X sees Y and does Z." Not "stakeholders" and not a heatmap for nobody.
7. **Close the loop.** Act → observe the outcome → self-evaluate → adjust (see §F). No past winner did this. It lifts C2, C3, AI-I and AI-T at the same time.
8. **"Why Z" as a requirement of the problem** (co-located in-stream decisions, or data that cannot leave the box). Not "we hosted it there."
9. **A public, live, honest repo** with a README that has the one-liner, diagram, how-to-run, results table, limitations and OSS links. The repo must match the video.
10. **GenAI bounded.** The predictive model decides, the LLM explains or extracts, and it is checked. It passes the delete-the-LLM test.

---

## §F Agentic closed-loop upgrades (user preference: act → observe → self-evaluate → adjust)
Every winner is open-loop: it predicts or displays, then stops. The projects a loop would have lifted most:
| Project | The loop it was missing | Why it would score |
|---|---|---|
| **Medikate** | predict miss-risk → send a tailored nudge or flag the pharmacist → observe whether the dose was taken → evaluate per-patient nudge effectiveness → adapt timing/channel (a bandit policy) | Turns prediction into intervention with measured uplift. Big C1 + AI-T gain, and the in-VM loop strengthens the "data never leaves" C3 story |
| **Hackasaurs** | forecast → set order quantities → observe actual waste/shortfall → self-score the forecast error → retrain/reweight daily | The cleanest closed loop; it makes "reduce waste" measurable instead of assumed |
| **CrisisLens** | raise a warning → observe whether an incident followed within N hours → recalibrate thresholds to a target false-alarm rate | Fixes its biggest weakness (no lead-time or false-alarm accountability) and the ethics critique |
| **URSI** | route a user → collect incident or user-safety feedback → re-weight segment scores → re-route | Replaces opinion-encoded labels with learned ones, so it gains real ground truth |
| **TradeSentinel / Uncalled coders (fraud)** | flag → analyst confirms or dismisses → online threshold or model update inside the transaction stream on Z | The textbook Z in-transaction story, with the feedback loop as the novelty |
| **Life Aspirant's** | detect plastic → dispatch a cleanup or drone check → verify removal in the next image pass → reprioritise hotspots | Moves from "detection" to "outcome", making its claimed metrics measurable |
Lower value from a loop: OcuGuard and BIG IRON (clinical loops need real outcome data, which you can't get in 24 h) and Farmer's Friend (season-long feedback).
**Caution for us:** the loop must actually run in the demo (at least a few simulated cycles with a visible metric improving or a threshold moving), with the self-evaluation metric shown. A loop drawn on a slide is just another overclaim (pattern 2).


---

<!-- §6: _ledgers/judge-advocate.md -->

# § Judge's advocate: what actually earned past IBM Z Datathon winners their places
Pass 2026-10-16. Written as an IBM manager on the 2026 panel would read it: harsh, but crediting real strengths.
Inputs: `../guidebook-digest.md` (2026 rubric), `past-winners.md` (projects + grades), `winning-criteria.md`.
I re-opened 7 repos with WebFetch to verify (URSI, CrisisLens, Medikate, Hackasaurs, BIG IRON, CodeCatalysts, Life Aspirant's). Fetched content was treated as data.
**Rule 4 reminder:** these are *patterns*. Every project here is off-limits as an idea.

## CATEGORY INDEX
- §A How to read these scores
- §B Per-winner verdicts (grade A/B entries)
- §C Grade-C entries (grouped, not scored)
- §D Score table
- §E The winning formula (checklist)
- §F White space: under-exploited problem shapes
- §G How a 2026 team beats the best of them, criterion by criterion
- §H Where an agentic closed loop would have lifted a winner
- §I Verification ledger

---

## §A How to read these scores
- Scored against the **2026** rubric: V = Value/theme · N = Novelty · T = Technical + LinuxONE + open-source AI · E = Execution/pitch (10 each). Plus the two AI Innovation Excellence criteria: **AI-O** (originality) and **AI-I** (transformational impact + technical excellence on LinuxONE).
- **E is partly inferred.** I haven't seen most videos. Placing is evidence the pitch landed, so E gets credit for that, capped where the repo contradicts the pitch.
- **The uncomfortable finding:** the 2025 judges clearly did *not* score T the way the 2026 rubric is written. The **Global 1st repo never mentions IBM** (verified). URSI ran on Watson Studio with empty `src/*.py` files. So past placings were driven by **V + E (story + visual)**. Under 2026 IBM-SME judging with an explicit LinuxONE criterion, several of them would drop.

---

## §B Per-winner verdicts

### Life Aspirant's — Plastic pollution in water (2025 Global 1st, grade B)
- **Why it won:** a big, visual, universally felt harm (plastic in water). A full-system *vision*: "IoT water sensors, drones, satellite imaging, and autonomous underwater vehicles" for "real-time detection, quantification, and forecasting". It's an early-warning shape ("detect hotspots, predict drift and accumulation zones").
- **Harsh read:** the repo is 1 notebook + `index.html`. No dataset described, no metrics, **no IBM anywhere** (cloud options listed are AWS/GCP/Azure). The 89/95/40% pitch figures are unsourced (DO NOT USE in `past-winners.md`). It won on vision and pitch, not build.
- **Scores:** V 8 (critical global need, clear Tech-for-Good) · N 5 (multi-modal sensing fusion is ambitious, but plastic detection itself is common) · T 2 (no LinuxONE, no evaluation) · E 6 (pitch clearly landed; claims don't survive a repo check) = **21/40** · AI-O 3 · AI-I 3.
- **Transferable lesson:** **a harm the judge can *see* in one image, plus an end-to-end "sense → forecast → warn" system story, carries enormous weight.** In 2026, back it with a build or an SME will dock it.

### Hackasaurs — Demand forecasting for public meal programmes (2025 Global 2nd, grade B)
- **Why it won:** reframed a commercial problem (retail demand forecasting) as **food waste in welfare canteens**. Multi-model stack (XGBoost main, LightGBM, LSTM), 70+ engineered features, a leakage-safe sklearn pipeline, R² 0.85–0.92 and a ₹700 crore loss figure (both from the gallery abstract, **not** the README), many dashboards plus a React frontend. This is the most "complete product" of the 2025 podium.
- **Harsh read:** the README has no metric values (one Actual-vs-Predicted image), no dataset description, and LinuxONE evidence is a "#CodingInLinuxOne" badge. Walmart-style sales data is not meal-programme data.
- **Scores:** V 7 (waste + hunger, credible beneficiary) · N 4 (demand forecasting is a textbook problem; the reframe is the only novelty) · T 5 (sound multi-model engineering; L1 is cosmetic) · E 7 (polished dashboards, a number-led pitch) = **23/40** · AI-O 3 · AI-I 5.
- **Lesson:** **a commodity model wins when it's re-aimed at a public-good beneficiary and shipped as a complete, polished, number-led product.**

### Gradient Ascent — OcuGuard AI, retinal triage (2025 Global 3rd, grade B−)
- **Why it won:** framed as **triage** (Urgent / Non-urgent / Normal) plus an advisory report, not bare classification. That's a decision-support shape with a clear output a clinician acts on.
- **Harsh read:** the repo is now 404, so nothing is verifiable. Fundus-image disease classification is one of the most common student ML projects.
- **Scores:** V 8 (preventable blindness, high stakes) · N 4 (common concept; the triage framing helps) · T 3 (unverifiable; no L1 evidence) · E 6 (the report artefact is a good demo end-state) = **21/40** · AI-O 3 · AI-I 4.
- **Lesson:** **turn a classifier into an action tier plus a human-readable report.** The output should be a *decision*, not a label.

### Tech Titans — TradeSentinel, trading fraud and collusion (Chennai 1st, grade B)
- **Why it won:** framed finance as **protecting retail traders**. Graph-ML for collusion rings, a transformer ensemble, behavioural biometrics, an LLM agent layer, an HMAC rolling-key "trust seal" and an immutable ledger. It is the most technically ambitious 2025 winner on paper.
- **Harsh read:** "IBM Z Crypto-Express-*inspired*". The abstract admits *"we have not used IBM features since they are not free."* Simulated data. An IBM SME would rate the platform story at near zero.
- **Scores:** V 6 · N 7 (graph collusion + a cryptographic trust seal is an unusual combination) · T 4 (rich stack, zero platform) · E 6 = **23/40** · AI-O 6 · AI-I 4.
- **Lesson:** **one atypical combination (graph ML + integrity crypto) reads as novel.** Mimicking a Z feature instead of using it is a 2026 liability.

### BIG IRON — Heart MRI second opinion (Chennai 2nd, grade A)
- **Why it won:** a concrete pain ("Radiologists in busy cardiac centers face mounting backlogs of MRI scans"), **explainability as the product** (Grad-CAM + Integrated Gradients overlays), an explicit human-in-the-loop line (a licensed cardiologist must review every prediction), and a real data plane (IBM COS for images, Db2 for case metadata and audit trail). There's a demo video and screenshots.
- **Harsh read:** MobileNetV2 transfer learning on "public cardiac MRI datasets" (unnamed). No numeric metrics in the README. IBM Cloud, not LinuxONE. "HIPAA-aligned" is unsubstantiated. The licence is proprietary.
- **Scores:** V 7 · N 4 · T 5 (good XAI + data plane, but not on L1) · E 7 = **23/40** · AI-O 3 · AI-I 5.
- **Lesson:** **show the model's reasoning visually and say who stays accountable.** Responsible-AI framing scores on V and E together.

### YuktiX — Fog/rain intensity map and weather anomalies (Bangalore 2nd, grade B)
- **Why it won:** a heatmap artefact plus a two-model split (RF to classify, IsolationForest for anomalies). Hub competition is shallow.
- **Harsh read:** fully synthetic data for 5,000 locations, a boilerplate README, 5 files.
- **Scores:** V 5 · N 3 · T 3 · E 5 = **16/40** · AI-O 2 · AI-I 2.
- **Lesson:** at hub level, **a clean map plus a classify-and-flag-anomalies pairing is enough to place.** It's the floor, not the target.

### Medikate (IBMLOND015) — Medication-adherence risk (London 1st, grade B) — **closest to a 2026 9-level build**
- **Why it won:** **inverted the obvious health project.** Not "diagnose disease" but "who is about to miss doses of an existing prescription". Non-adherence is called "a major preventable cause of harm". A named user (GPs). It has a real modelling choice that matches the data's shape: a tabular Transformer with an **ordinal head** (3 ordered risk tiers), Ordinal Focal Loss, weighted sampling, early stopping on macro-F1. **Honest per-class metrics** are reported: acc 0.85, macro-F1 0.79, "Likely" tier P 0.65 / R 0.77 on n=200, so the weak class is visible, not hidden. There's a full-stack GP dashboard (FastAPI + React + Postgres), with FastAPI served on LinuxONE.
- **Harsh read:** the README *claims* "Runs on IBM Z Confidential Computing" and OpenShift multi-tenant scaling, with no evidence either was built. That's exactly the overclaim the 2026 SMEs are told to catch.
- **Scores:** V 7 (prevention, an overlooked user) · N 6 (adherence + ordinal framing is a genuine inversion) · T 7 (modelling fits the problem, honest eval, served on L1; docked for unbuilt CC claims) · E 7 = **27/40** · AI-O 6 · AI-I 6.
- **Lesson:** **pick the model *because of* the shape of the target (ordinal, imbalanced) and report the weak class honestly.** That's what an SME recognises as engineering.

### AlphaPeterGamma — CrisisLens, riot early warning (London 2nd, grade A) — **highest novelty**
- **Why it won:** an early-warning framing for a public harm (communal riots). A non-trivial, original pipeline: PoliBERTweet embeddings → KNN influence graph → **attention GNN** → influence scoring → crisis heatmaps. It contrasts event vs non-event data (`Event_Data_cleaned_locations.csv` vs `Non_Event_…`), and "all code was written on the IBM Z jupyterlab environment."
- **Harsh read:** the README is two sentences. No metrics shown. They call their own repo "messy". Influence on social media ≠ violence causation, and the false-alarm cost isn't discussed.
- **Scores:** V 7 · N 8 (a graph-of-influence approach to unrest is genuinely unusual) · T 6 (sophisticated, all on L1, but unevaluated and not productionised) · E 6 = **27/40** · AI-O 8 · AI-I 5.
- **Lesson:** **the novelty lives in *how signals are connected* (a graph), not in a bigger model.**

### IBMGER004 — Interstate conflict early warning (Germany 1st, grade B)
- **Why it won:** **data fusion nobody joins**: UCDP conflict levels + UN trade + IMF GDP, so trade interdependence becomes a conflict predictor. It started with a simple NN and moved to an LSTM, trained "on IBM Z".
- **Harsh read:** a modest model. Evaluation and demo details are unknown. A GitLab repo on a university instance.
- **Scores:** V 7 · N 6 (the fused-signal hypothesis is the idea) · T 4 · E 5 = **22/40** · AI-O 4 · AI-I 4.
- **Lesson:** **a crisp causal hypothesis ("A predicts B") tested on authoritative public datasets is itself the novelty.**

### AnalytIQ — URSI, Urban Route Safety Index (South Africa 1st, grade A; the 2026 guidebook's showcase)
- **Why it won:** the best **human framing** of any winner. Women and evening-shift workers, whose mobility to work and education is limited by fear of crime. An explicit audience list (women, commuters, students, Community Policing Forums, planners). Fusion of SAPS crime + OSM streetlights/roads + Johannesburg GIS transport. The README literally has a "**Wow factor**" section: "streets **color-coded by safety score**". And a goal line: "Making **safety a quantifiable and visible metric**".
- **Harsh read:** "Weighted Scoring / Logistic Regression" with undefined weights. "PSI" is never defined. No evaluation metric. Watson Studio, not LinuxONE. `src/*.py` files are empty. And safety routing alone does *not* win (HaloMap, SurakshaMap, weWalk didn't place), so the framing + fusion + map did the work.
- **Scores:** V 9 · N 6 (the infrastructure × crime fusion; safety routing itself is common) · T 2 · E 7 = **24/40** · AI-O 3 · AI-I 4.
- **Lesson:** **name the person, list who benefits, and design one "wow" visual on purpose.** URSI planned its wow moment in writing.

### Izimpisi ze-Data — public-fund misallocation (South Africa 2nd, grade B−)
- **Why it won:** a locally urgent harm (corruption in the health budget), with anomaly detection.
- **Harsh read:** synthetic data ("couldn't find SA data") and a repo that's now 404.
- **Scores:** V 7 · N 5 · T 2 · E 5 = **19/40** · AI-O 3 · AI-I 3.
- **Lesson:** **local relevance to the hub's judges counts.** Disclosed synthetic data is tolerated.

### CodeCatalysts — hate-speech moderator (2023 2nd, grade A) — **deepest platform work**
- **Why it placed:** BERT fine-tuned on ~25k labelled tweets with weighted BCE, 95% accuracy (no P/R/F1). Per the author's IBM blog (not the README): **deployed on L1CC in s390x Docker, <1 s inference, and fixed big-endian weight loading.**
- **Harsh read:** a commonplace problem, and an accuracy-only metric on an imbalanced task. The README doesn't document any of the platform work, so a judge reading only the repo would miss it.
- **Scores:** V 6 · N 3 · T 7 · E 5 = **21/40** · AI-O 3 · AI-I 5.
- **Lesson:** **real s390x engineering (containers, endianness, measured latency) is exactly what the 2026 T criterion wants. Put it on screen and in the README, not only in a later blog.**

### Uncalled coders — transaction fraud (2023 2nd, grade B)
- A single notebook, generic RF/NN, a template README. **V 4 · N 1 · T 3 · E 3 = 11/40** · AI-O 1 · AI-I 2. Lesson: the rubric's "commonly available" band is real. This placed in a weaker year, and wouldn't in 2026.

### Fantastic Four — Farmer's Friend (2021 3rd, grade B)
- Crop recommendation + mixed-crop clustering from merged rainfall/climate/fertiliser data. A decision tree "99%" is a red flag (likely leakage or an easy target). **V 6 · N 3 · T 2 · E 4 = 15/40** · AI-O 2 · AI-I 2. Lesson: a livelihoods framing for a named group (smallholder farmers) carries a basic model.

---

## §C Grade-C entries (grouped, not scored: too little evidence)
- **2025 Bangalore 1st "RUNTIME TERRORS":** ambiguous between Dedcell (passwordless WebAuthn + keystroke one-class SVM) and an alternative credit-scoring / fairness project. Both point the same way: *protection or inclusion framing on a security/finance base*.
- **2023:** Data Detectives (London 1st), Carmex–Lambda Prime (Bangalore 1st), RIP_ENGINEERS, Ctrl Alt Del (Mentor), Code Wizards, Data_R_Us, Starfall stallions. Projects unknown.
- **2023 Imperial team** (tweet → charitable-cause classifier → link to charities): LLM labelling + XGBoost + embeddings on LinuxONE. Pattern: **LLM used for data labelling, a classical model for the decision.** That's a bounded-GenAI pattern worth noting.
- **Team Oasis** (lake-encroachment CNN in Docker on L1CC; year and place unclear): pattern is *satellite imagery + container on L1 + an endianness fix*.
- **2019 Berkeley precursor** (student finance, wildfire, homelessness): judges favoured "large datasets or real-time data, since the mainframe's strength is quickly crunching data."

---

## §D Score table (2026 rubric, strict)
| Project (place) | V | N | T | E | **/40** | AI-O | AI-I |
|---|---|---|---|---|---|---|---|
| Medikate (London 1st 2025) | 7 | 6 | 7 | 7 | **27** | 6 | 6 |
| CrisisLens (London 2nd 2025) | 7 | 8 | 6 | 6 | **27** | 8 | 5 |
| URSI (SA 1st 2025) | 9 | 6 | 2 | 7 | **24** | 3 | 4 |
| Hackasaurs (Global 2nd 2025) | 7 | 4 | 5 | 7 | **23** | 3 | 5 |
| TradeSentinel (Chennai 1st 2025) | 6 | 7 | 4 | 6 | **23** | 6 | 4 |
| BIG IRON (Chennai 2nd 2025) | 7 | 4 | 5 | 7 | **23** | 3 | 5 |
| IBMGER004 (Germany 1st 2025) | 7 | 6 | 4 | 5 | **22** | 4 | 4 |
| Life Aspirant's (Global 1st 2025) | 8 | 5 | 2 | 6 | **21** | 3 | 3 |
| OcuGuard (Global 3rd 2025) | 8 | 4 | 3 | 6 | **21** | 3 | 4 |
| CodeCatalysts (2nd 2023) | 6 | 3 | 7 | 5 | **21** | 3 | 5 |
| Izimpisi (SA 2nd 2025) | 7 | 5 | 2 | 5 | **19** | 3 | 3 |
| YuktiX (Bangalore 2nd 2025) | 5 | 3 | 3 | 5 | **16** | 2 | 2 |
| Farmer's Friend (3rd 2021) | 6 | 3 | 2 | 4 | **15** | 2 | 2 |
| Uncalled coders (2nd 2023) | 4 | 1 | 3 | 3 | **11** | 1 | 2 |

**Read-across:** nobody clears 30/40 under the 2026 rubric. Column V averages ~7, but **T averages ~4 and nobody tops 7.** The ceiling among past winners is low, and it is lowest on Technical/LinuxONE. No winner scores above 8 on AI-O, or above 6 on AI-I.

---

## §E The winning formula (checklist for a 2026 team)
1. [ ] **A named person + a visible harm + one sourced number** in the first 15 s (URSI's women commuters; BIG IRON's MRI backlog; Medikate's preventable harm).
2. [ ] **A "who benefits" list** with 3–5 audiences, including an institutional actor who would *use* the output (URSI: CPFs, planners).
3. [ ] **Decision shape, not a label:** detect → score into an action tier → tell a human what to do (OcuGuard's triage, Medikate's 3 risk tiers).
4. [ ] **One atypical ingredient** in a familiar problem: an unjoined data fusion (IBMGER004, URSI), an inversion (Medikate), or a relational structure (CrisisLens's graph).
5. [ ] **A model chosen for the target's shape** (ordinal / imbalanced / relational / temporal), with **honest per-class metrics vs a baseline**, including the weak class.
6. [ ] **One designed "wow" visual**, written down in advance (map, heatmap, explanation overlay, triage report).
7. [ ] **Responsible-AI line:** who stays accountable, what happens when it's wrong (BIG IRON).
8. [ ] **LinuxONE as a proven requirement:** served from a container on the s390x VM, measured latency/throughput, encryption shown, **screenshots and on-screen terminal**. No "inspired-by" or unbuilt Confidential Computing claims.
9. [ ] **A repo that survives an SME's 2-minute check:** README with the one-liner, data sources, metrics table, how to run, limitations, and platform evidence (CodeCatalysts hid its best work in a blog).
10. [ ] **Local resonance** with the hub's judges where it fits naturally (UK data, UK services). Izimpisi and URSI used national data.

---

## §F White space: under-exploited problem shapes
Winners cluster in **public-safety early warning** (URSI, CrisisLens, IBMGER004, TradeSentinel), **medical image classification** (OcuGuard, BIG IRON) and **environmental detection** (plastic, fog). Under-exploited:
1. **Theme 2 for real: privacy-preserving AI that is actually built.** Zero winners implemented privacy tech. Medikate and BIG IRON only *claimed* it. Measured privacy (a re-identification test, encrypted inference, data that never leaves the VM) on LinuxONE is an empty lane, and it's the platform's home turf.
2. **"Who is about to be missed" / continuity of care and services.** Medikate is the only prevention-by-omission winner. Missed appointments, benefit drop-off, care-leaver disengagement and safeguarding gaps are prevention, not diagnosis.
3. **Act, not just warn: allocation and dispatch under scarcity.** Every winner stops at a score or a map. None decides *where to send the finite resource* (inspectors, outreach workers, maintenance crews) and checks the outcome.
4. **Accessibility and disability** (a 2026 T3 sample prompt): 0 of 12 winners.
5. **Education:** 16% of the 2025 field, 0 winners. The field tried it and the framing hasn't cracked it yet, so a sharp harm-led angle could stand out.
6. **Critical-infrastructure reliability** (water, energy, transport assets): only fog/weather touched it, and that was weak.
7. **Inverted fraud: protecting the victim** (authorised-push-payment scams, elder financial abuse) rather than the institution. TradeSentinel gestured at this.
8. **Streaming at genuine rate on LinuxONE.** No winner processed a live stream with measured per-event latency, even though the 2019 judges said exactly this "stood out", and it is literally 2026 Theme 1.

---

## §G How a 2026 team beats the best of them, criterion by criterion
- **V (best: URSI 9):** match URSI's named-person framing, *and* add what URSI lacked: a quantified "what changes" estimate with its assumption shown, plus a responsible-AI line. That's a 9–10.
- **N (best: CrisisLens 8):** the novelty must be structural (fusion, inversion, graph, closed loop), and it must pass the anti-wrapper and "afternoon" tests in `winning-criteria.md` §C. Beat 8 with an atypical combination *plus* an evaluated mechanism (CrisisLens never showed it worked). A closed adaptive loop is a novelty lever no winner used.
- **T (best: Medikate / CodeCatalysts 7):** the cheapest 3 points in the contest. Containerised model on s390x + measured p50/p95 latency + hardware-crypto proof (`/proc/crypto`, `openssl speed`) + an honest per-class eval vs a baseline + an `nnpa` check (claim Telum only if present). Past winners topped out at "FastAPI on the VM" or "Docker + endianness fix".
- **E (best: ~7):** a scripted 2:50 video that starts with the product, has one planned wow moment (URSI-style, in writing), shows the live LinuxONE terminal, and has every member visible. Plus a repo that matches the video (Devfolio-style claim-vs-code audits now exist).
- **AI Innovation award:** no past winner scores above 8 / 6. It needs high N *and* T simultaneously: an original AI mechanism that's *measured* on LinuxONE, with a scale story grounded in your own numbers.

---

## §H Where an agentic closed loop (act → observe → self-evaluate → adjust) would have lifted a winner
- **Hackasaurs:** forecast → kitchen cooks to it → observe actual leftovers → retune the per-site safety stock. A natural loop that turns a forecast into a self-correcting procurement agent. Would raise N +2 and AI-I +2.
- **Medikate:** flag high-risk patient → trigger outreach (SMS/pharmacist call) → observe refill → learn which intervention works for which tier. This moves from prediction to an uplift/bandit policy, which is genuinely novel for the field.
- **CrisisLens:** alert → observe whether incidents followed → recalibrate per-region thresholds to a fixed false-alarm budget. That fixes its biggest credibility gap (unmeasured false alarms).
- **URSI:** suggest route → collect incident reports / user feedback → reweight segment scores. The static index becomes a learning one.
- **Life Aspirant's:** forecast drift → dispatch the drone/sensor to the highest-uncertainty zone → update the model (active sensing). That would have made the "system" vision real.
- **Caveat for 2026:** a loop scores only if it is (1) actually running in the demo, at least as a simulated multi-step episode; (2) logged, with each cycle's metric visible; (3) bounded by safety rules (a human approves high-stakes actions). An LLM "agent" that just narrates is a wrapper and fails `winning-criteria.md` §C.

---

## §I Verification ledger (this pass)
| Source | Verdict | Note |
|---|---|---|
| github.com/thetomaunatlala-777/AnalytIQ--URSI- | KEEP | Audiences, "Wow factor", Watson Studio, no metrics: all confirmed |
| github.com/notacountry/IBM-Z-Datathon | KEEP | "We won 2nd place"; L1 Jupyter quote; no metrics; file names show the pipeline |
| github.com/Neesay/IBM-Z-Datathon-2025-Team-15-EdizSlow | KEEP | Ordinal tabular Transformer, per-class metrics, unbuilt Confidential Computing claim confirmed |
| github.com/Yukesh-30/IBM_DATATHON_HACKASOURS | WEAK for metrics | README shows no R² or ₹ figures; those come only from the gallery abstract (`past-winners.md`) |
| github.com/ShivrajRajasekaran/…Heart-MRI… | KEEP | MobileNetV2, Grad-CAM + IG, COS + Db2, no numeric metrics, proprietary licence |
| github.com/chrehall68/SSF23-CodeCatalysts | WEAK for platform | README has no s390x/Docker/endianness content; that rests on the author's IBM blog (KEEP in `past-winners.md`) |
| github.com/teja-cmd/Plastic-Detection-in-Water-Resources | KEEP | Confirms: no IBM mention, no data or metrics; vision-only README |
| Scores in §D | judgement | My strict reading as a 2026 panellist. E is inferred from placing where no video was seen. |


---

<!-- §7–§8 (idea-selection critiques for other ideas) archived 2026-10-18: _archive/2026-10-18-pre-merge/research-section7-8-other-ideas.md -->

<!-- §9: Blacknaught research passes, 2026-10-17 -->

# § 9. Blacknaught research (red team + 4 protocol passes), 2026-10-17
The chosen project is **Blacknaught** (formerly Dark Hours v2). The PRD is `BLACKNAUGHT-PRD.md`. These passes followed CLAUDE.md §10. Reddit and HN were blocked or returned nothing in every pass, so community input comes mainly from local press, forums and maker sites.

## CATEGORY INDEX
- 9.1 Country scope and filters
- 9.2 Outage data sources (target countries + GB)
- 9.3 Independent confirmation signals
- 9.4 Grid frequency
- 9.5 Duration prediction
- 9.6 Law, operators, alert channels
- 9.7 Devices, harm, backup power
- 9.8 s390x stack and security
- 9.9 DO NOT USE (quarantine)

## 9.1 Country scope (KEEP)
| Claim | Sources | Verdict |
|---|---|---|
| Bangladesh and Pakistan are lower-middle income (FY2027); Indonesia, Sri Lanka and South Africa are upper-middle | World Bank API + FY27 classification; AsiaNews (Sri Lanka upgrade) | KEEP |
| Out-of-pocket health spending: Bangladesh 79.3%, Pakistan 52.9%, Indonesia 31.1% (2023) | World Bank WDI API; BIDS/UNB | KEEP |
| Firms experiencing outages: Bangladesh 71.4%, Pakistan 50.7%, Indonesia 12.7% | WDI IC.ELC.OUTG.ZS | KEEP |
| Pakistan: 75.2 outages a month (2013) | Enterprise Surveys API; Al Bawaba 2015 | KEEP (dated) |
| Bangladesh crisis in 2026: 3,757 MW peak shedding; Khulna 13–14 h a day | BPDB; Observer; Dhaka Tribune | KEEP |
| K-Electric very-high-loss feeders: 12 h 14 min of outage a day (Sept 2026) | NEPRA; Tribune | KEEP |
| No home medical-dependency register at any utility in BD, PK or ID | Research passes 1 and 2 (facility exemptions only) | KEEP |

## 9.2 Outage data sources (KEEP unless marked)
- **PGCB hourly**, Bangladesh national, 2015–Mar 2026, CC BY 4.0 (Mendeley vpk8spw2mm). Corroborated by BPDB data. KEEP.
- **BPDB daily PDFs**, 9 zones of demand, supply and shed MW, live as of 14–17 Oct 2026; text layer parses with pdftotext. Corroborated by the BPDB Mendeley dataset (x7r7wdb39k, CC BY). KEEP.
- **NEPRA performance reports**: SAIDI/SAIFI per distribution company; scanned PDFs needing OCR. Corroborated by Business Recorder. KEEP.
- **K-Electric and LESCO feeder schedules**: images and an app only, no API. Content KEEP, access WEAK.
- **GB live faults, checked live**:
  - UKPN anonymous JSON worked once, but the portal also shows a login wall → WEAK.
  - Northern Powergrid: 465 records → KEEP.
  - SSEN PowerTrack, with feeder IDs plus priority and critical customer counts → KEEP.
  - SP ENW and SPEN need a free login. NGED returned HTTP 520.
- **ENWL historic unplanned outages**: 312,936 records from 2000, CC BY 4.0, free registration. Corroborated by the ENWL GSP page. KEEP.
- **EAGLE-I**: 15-min US county outages, 2014–2025. Scientific Data 2024; ORNL DOI. KEEP.
- Indonesia PLN: aggregates only. WEAK.
- Central Asia: no open data. WEAK.
- India NFMS: behind a login. WEAK.
- Ghana nLine GridWatch: household-level, 2018–24, access unconfirmed. WEAK.

## 9.3 Independent signals
- **IODA**, free and keyless, 5–10 min:
  - Caught Bangladesh on 4 Oct 2022: 370 min from 09:40 UTC, matching news reports of about 7 h. KEEP.
  - Caught Pakistan on 23 Jan 2023, but only at province level. Rule: always query admin-1, not just country.
  - A shared artefact on 2026-06-20 fired in 4 countries at once. Rule: discard events that fire in ≥3 unrelated countries within ±10 min.
- **Cloudflare Radar annotations** (POWER_OUTAGE cause; curated, so hours of delay): KEEP as labels.
- **NASA Black Marble**: daily; cloud and monsoon artefacts. WEAK for real time.
- **Klugman et al., IPSN 2021**: plug-in sensors found about 2× the outages the utility recorded. Corroborated by CEGA and MCC. KEEP.

## 9.4 Grid frequency
- **Elexon Insights FREQ**: GB, 15 s, keyless, about 1.5 min lag (checked live). No push stream: `/system/frequency/stream` returns 404, so poll. KEEP.
- **NESO**: 1-s historic monthly CSVs from 2014 to Sep 2026; no real-time product. KEEP.
- **ESO report on 9 Aug 2019**: LFDD at 48.8 Hz, 931 MW, about 1.1 M customers, 15–45 min. Via Ofgem. KEEP.
- **No public live frequency** for Pakistan, Bangladesh, Indonesia or Uzbekistan. FNET/GridEye data needs authorisation.
- **NEPRA 13 Oct 2022 inquiry**: 49.9 → 48.6 Hz, then a North/South split. KEEP.
- **Pakistan 23 Jan 2023**: over-frequency to 50.75 Hz (an NTDC note, reported by Reuters). KEEP from a single source; ARY and Profit corroborate the split.
- **Bangladesh 2014** (BUET/EU study, 2023): 50.33 → 48.65 Hz in 6.8 s; UFLS stages at 48.9/48.8/48.7 Hz; only 415 of 1,001 MW was shed; blackout in about 59 s; no AGC; low inertia. KEEP.
- **Iberia 2025** (ENTSO-E final report): overvoltage came first. KEEP.
- **Frequency is common across a grid only on timescales of about 10 s or more**, and not during a split. Rydin Gorjão, Nature Communications 2020. KEEP.
- **Kruse et al.** (IEEE Access 2020; Patterns 2021): frequency is predictable, and its residuals are useful as an anomaly score. KEEP.
- **NERLDC India 1-s PMU data**, CC BY 4.0. KEEP; it is a different synchronous area.
- **Early-warning signals** (Hines 2011, Hurst exponent): WEAK.
- **DIY frequency meters**: need a good clock source and isolation; maker sources only. WEAK.

## 9.5 Duration prediction
- **NETL/NREL IEEE Access 2024**: outage magnitude is the main predictor, and a log-linear model is about as good as AFT. KEEP.
- **Exelon arXiv 2505.00225**: 36.9% lower ETR error. Preprint written by the utility → WEAK alone; NJ BPU corroborates the claim that ETRs are inaccurate.
- **Transfer learning with cluster ensembles**, IEEE TPWRS 2024. KEEP.
- **Metrics:** Brier score at the horizon, C-index, calibration plots.
- **Pitfalls:** censoring, storm skew, mixing planned and unplanned outages, and censored demand during load-shedding.

## 9.6 Law, operators and alert channels
- **Indonesia**: PDP Law 27/2022 in force since Oct 2024, with vital-interest and public-interest bases. GR 33/2026 takes effect 16 Jan 2027. KEEP (DLA Piper; Rajah & Tann).
- **Bangladesh**: PDP Ordinance gazetted 6 Nov 2025; Bill passed 9 Apr 2026; consent is mandatory. KEEP (TBS; Prothom Alo; Dhaka Tribune).
- **Pakistan**: no data-protection law. PECA s.16 applies, and hospital data needs regulator authorisation to move. KEEP (DLA Piper).
- **Emergency alerts**: no live cell broadcast in Bangladesh, Pakistan or Indonesia.
  - Pakistan: NDMA geo-SMS; PTA can order operator SMS.
  - Indonesia: SMS plus digital-TV warnings.
  - Bangladesh: the 1090 voice line.
  - KEEP.
- **Responders**: Lady Health Workers and Rescue 1122 in Pakistan. KEEP (headcount figures dated).

## 9.7 Devices, harm, backup power
- **Static oxygen concentrators**: 0 h on battery; cylinder backup 8–20 h; draw 350 W. NHS Highland, Royal Devon, Philips. KEEP.
- **Ventilator battery**: Trilogy Evo 15 h. Philips datasheet. KEEP.
- **Ghana facility mortality**: +43% for each day with more than 2 h of outage (Apenteng 2018). KEEP, dated.
- **WHO Energizing Health 2023**: KEEP.
- **Do et al. 2023**: an 8 h outage is the medically relevant threshold. KEEP.
- **Pakistan solar imports**: 17 GW in 2024, skewed to high-income households. Ember via Profit; Business Recorder. KEEP.
- **Karachi 2024 heatwave deaths blamed on load-shedding**: disputed → WEAK.
- **PFD reports**:
  - Peter Coates: rang 999 himself and got Category 2. The coroner's concern is the gap between ambulance categories, not welfare calls. KEEP, with the corrected framing.
  - Janette Palmer: supported-living block missing from the PSR. KEEP.

## 9.8 s390x stack and security (verified against PyPI, Docker Hub, Debian and GHCR)
**Works ✅:**
- fastapi, plain uvicorn, pydantic-core
- psycopg 3 (pure)
- Docker images: postgres, redis, mosquitto
- APScheduler, paho-mqtt, httpx
- llama.cpp `server-s390x` (needs big-endian GGUF)
- MapLibre GL JS globe (runs in the browser)

**Doesn't work ❌:**
- uvicorn[standard], asyncpg, psycopg-binary
- TimescaleDB, PostGIS Docker images
- scikit-survival, h3
- LangGraph (Rust dependencies)
- numpy, pandas, torch, cryptography from PyPI (use the IBM image or distro packages)

**Security:**
- OpenSSL 3.5 brings ML-KEM/ML-DSA, with X25519MLKEM768 as the default (Phoronix; Help Net Security). KEEP.
- k≥11 aggregation precedent: HHS emPOWER. KEEP.

## 9.9 DO NOT USE (quarantined)
| Claim | Refuted by |
|---|---|
| Sri Lanka, Indonesia or South Africa are lower-middle income | World Bank FY2027 |
| South Africa or Zambia have ongoing load-shedding in 2026 | SAnews 504+ days without it; Lusaka Times / ZNBC |
| A third party can trigger national emergency alerts | gov.uk; Kenya CA; Tesco Mobile |
| "A welfare call would have saved Peter Coates" | The PFD text |
| NEOP/Arup has a public API | None found; use each network operator's NEO datasets |
| Elexon has a frequency websocket/push stream; NESO has real-time frequency | Live checks (404; portal lists historic data only) |
| FNET has frequency recorders in BD/PK/ID/UZ | Not confirmable |
| "Guddu at 57 Hz"; under-frequency caused the Bangladesh 2022 blackout | NTDC note; PGCB probe |
| Blackouts are always preceded by under-frequency | Pakistan 2023 (over-frequency); Iberia 2025 (overvoltage) |
| A torch-nnpa or ibm-zdnn-plugin PyPI package; llama.cpp GGML_NNPA flag | Not on PyPI; flag removed upstream (use the image's plugin) |
| Afrobarometer "own electricity source" read as generator-ownership rates | Its catalogue says the figures can't be read as summary statistics |
| Household inverter/generator ownership rates for BD or ID | No source found; don't estimate |

---

# § 10. Blacknaught research passes 2, 2026-10-17 (datasets · country factors · gap hunt · PRD teardown)
⚠ The session's shared web-search cap (200) ran out during these passes. Items marked "verify" need a re-run once `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` is raised. Reddit, HN and Quora were unreachable; community input comes from Kaggle signals, practitioner sites and developer sites.

## 10.1 Datasets (KEEP)
- **ENWL unplanned outages**: 312,936 records, 25 fields, CC BY 4.0, free registration. Confirmed by the OpenDataSoft API and Open Net Zero.
- **UKPN IIS**: 316,435 records with restoration stages, CC BY 4.0, registration.
- **NESO 1-s frequency**: Jan 2014 to Sep 2026, 153 files; time zone GMT before 2019 and UTC from 2019.
- **NESO historic demand**: 2001–2026, half-hourly.
- **PGCB hourly** (Mendeley + UCI #1175): demand is censored during shedding, and shed MW is an estimate.
- **BPDB daily** (Mendeley x7r7wdb39k): 2019–2024.
- **PNNL OEDI 6458** (EAGLE-I × DOE-417): CC BY 4.0.
- **London Smart Meters** (Kaggle): ODbL.
- **ESPENI** (Zenodo): CC BY-**NC**.

**WEAK:** EAGLE-I raw (rights unclear), PRECON (1 year only), UCI duplicate, OPSD (stale).

**DO NOT USE:**
- Kaggle ESPENI mirror (relabels NC as CC0).
- Kaggle PGCB re-uploads (identical bytes, rewritten licences).
- `harpree` grid-frequency (1 hour of data).
- Synthetic "smart grid" Kaggle sets.
- `belbino` "global" set (actually US).

**IBM:** no grid or outage data on Kaggle (`ealtman2019` holds only AML and TabFormer), Hugging Face or DAX.

## 10.2 Methods
- hmmlearn GaussianHMM (EM can hit local optima, so use multiple starts).
- sklearn `adjusted_rand_score` and `StratifiedGroupKFold` (best-effort when groups are large).
- scipy: wasserstein_distance, ks_2samp, levene(center='median').
- **PSI 0.1/0.25:** industry rule of thumb with no academic basis; depends on bins and sample size (Yurdakul 2018; Yurdakul & Naranjo 2020). KEEP as a caveat.
- Cliff's delta thresholds (Romano 2006): unverified.
- Kleinberg et al. 2016: calibration and balance cannot all hold at once. KEEP.

## 10.3 Country grid parameters (from grid codes, read in full)
| | GB | BD | PK |
|---|---|---|---|
| Nominal frequency | 50 Hz (ESQCR reg 27) | 50 Hz (BERC Grid Code 2018) | 50 Hz (NEPRA Grid Code 2023 / PSDR 2024 draft) |
| Operating bands | 49.8–50.2 normal; ±1% statutory; outside 49.5–50.5 for ≤60 s; LFDD from 48.8 | 49.5–50.5 normal; operator ladder at 49.5 / 49.3 / 49.1; 2014 UFLS at 48.9 / 48.8 / 48.7; no RoCoF relays; no AGC; 3 river regions | 50 ± 0.05 target; 49.8–50.2 sensitive; 49.5–50.5 tolerance; contingency 49.3; 6,133 MW/Hz regulation; 0.5 Hz governor dead band in practice |
| Voltage | 230 V +10/−6% | LV 220/230 V unverified | 230 V ±5% |
| Interruption definition | ≥3 min | — | Long >5 min; **SAIDI excludes generation and transmission** |
| Planned outages (PK) | — | — | Residential and commercial shed first; 48 h notice; seasonal windows |

- **T&D losses** (World Bank 2024): BD 8.19%, PK 15.16%.
- **Pakistan 2023 blackout:** after the grid split, the south rose to 51.5 Hz.

**DO NOT USE:**
- "BEGC 49.5–51.5" (typo in the EU report).
- "BD standard frequency 49 Hz" (press error).
- "BD T&D losses one-third" (Wikipedia, refuted).
- "PK contingency band 49.4" (superseded).

## 10.4 Gap hunt (KEEP unless marked)
- **Klugman IPSN'21** (text extracted): 3 sensors per site; ≥2 must co-report; ST-DBSCAN radius 2.4 km; about 74% uptime; single-sensor events rejected.
- **dontkillmyapp:** Android OEMs (Xiaomi and others) kill background apps, so phone-based sensing is unreliable.
- **Bangladesh prepaid meters:** 11.85% in 2022 (Daily Star); DESCO about 56%, DPDC about 30%, BREB under 4% (Dhaka Courier 2022). The 2026 figure of 87.5 lakh is WEAK.
- **Prothom Alo, Apr 2026:** Dhaka spared; REB areas cut 6–8 h a day; REB figures exceed PDB/PGCB.
- **Kinshella 2021:** Lady Health Workers went unpaid for months; coverage 0.24–0.97 per 1,000.
- **JAMIA 2026:** alert fatigue is poorly defined; measure it as a drop in appropriate responses.
- **Breaches in the target countries:**
  - Bangladesh bdris leak, about 50 M records (TechCrunch 2023).
  - Pakistan NADRA, 2.7 M records with insider involvement (DRF 2024).
- **HHS emPOWER:** counts of 1–10 masked as 11; the CMS cell-size rule; over 3 M Medicare users of electricity-dependent equipment; an "emPOWER AI" product exists.
- **Australia NERR enforcement** (ESD News): EnergyAustralia A$12 M; Origin A$12 M (unregistered up to 188 days; disconnected up to 66 days).

**WEAK:**
- PG&E Medical Baseline covered about 10% in Napa (CCLHO letter).
- BD peritoneal dialysis under 2%.
- BD DHIS2 and mPower integration figures.
- UNICEF concentrators went to facilities.
- Alert override rates of 46–96%.

**Verify:** NERR's 4-business-day notice rule; CAPD power-independence (ISPD citation); BD PDP lawful bases; GSMA gender gap in phone ownership.

**DO NOT USE:**
- Any home-oxygen, ventilator or dialysis patient count for BD or PK.
- "COVID concentrators went to homes."
- "An IPS can't run a concentrator" stated as absolute.
- "Nobody anywhere tracks these patients."

## 10.5 PRD teardown (verified)
- Granite 3.3 2B covers 12 languages, **not Bengali or Urdu** (Hugging Face model card; Ollama).
- The IBM TF zDNN plugin accelerates **inference**, not training (IBM tutorial).
- Elexon `/system/frequency` returns a whole day unless `from` and `to` are passed.
- MapLibre v5 globe interpolates to Mercator on zoom.
- `openssl genpkey -algorithm ML-DSA-65` works on OpenSSL 3.5; the `pkeyutl` path is untested.
- XGBoost `survival:aft` on s390x is untested: check on the VM in hour 1.

---

## Pivot critique pass — UK fault-data + LinuxONE (2026-10-17)
**The pivot, in one line:** train a fault/outage model on UK data (NESO and others), feed it "hypothetical sensor" readings, alert people before outages, then "just input" Pakistan/Bangladesh frequency and voltage. Add a per-home voltage/frequency graph. Everything trained and run on LinuxONE.
**Verdict:** survivable, but only as an **input upgrade to the existing PRD**, not a replacement. NESO can't find faults. The UK fault-history data (ENWL/UKPN) can rank *where* faults recur. Medical triage stays the decision.
Reddit and StackExchange are blocked for our fetcher (HTTP 400). Community input comes from papers that use the Kaggle sets and Kaggle usage signals.

### CATEGORY INDEX
- 11.1 What NESO data can and can't do
- 11.2 Fault / voltage dataset comparison
- 11.3 Transfer to Bangladesh / Pakistan
- 11.4 Household view and privacy
- 11.5 LinuxONE fit (training, NNPA)
- 11.6 Community consensus
- 11.7 Final call
- 11.8 DO NOT USE (quarantine)

### 11.1 What NESO data can and can't do (KEEP)
| Claim | Sources (fetched today) | Verdict |
|---|---|---|
| NESO publishes **GB system frequency at 1 s**, monthly CSVs, NESO Open Data Licence, latest file Sep 2026. **No voltage and no location fields.** | [NESO System Frequency](https://neso.energy/data-portal/system-frequency-data); ledger §10.1 | KEEP |
| Frequency reflects the **national supply–demand balance**. It is not a local fault signal | [NESO "What is frequency?"](https://www.neso.energy/energy-101/electricity-explained/how-do-we-balance-grid/what-frequency); [Rydin Gorjão et al., Nat Commun 2020](https://arxiv.org/abs/2006.02481v1) (local oscillations become "homogeneous bulk behaviour" across a synchronous area) | KEEP |
| So NESO frequency **cannot localise a fault**. It can flag **system events** (9 Aug 2019: LFDD at 48.8 Hz) and grid stress | The two above + ESO 9 Aug 2019 report (ledger §9.4) | KEEP |
| **ENWL historic unplanned outages** give location, time, duration and cause back to 2000. Registration needed | [Open Net Zero ENWL page](https://www.opennetzero.org/electricity-north-west/unplanned-outages1); ledger §10.1 (312,936 records via the ODS API) | KEEP. ⚠ Today's Open Net Zero page lists the licence as **"unknown"**, but ledger §10.1 said CC BY 4.0. **Confirm the licence on the ENWL portal at download** |
| ⇒ The honest version of "historical analysis of what's likely to fail" is **per-area fault recurrence + duration on ENWL, validated on UKPN**. It is not a NESO frequency model | Synthesis of the rows above | KEEP |

### 11.2 Fault / voltage dataset comparison
**KEEP (use these)**
| Dataset | Real? | Licence | Size | Labels | Time to use | Verdict |
|---|---|---|---|---|---|---|
| **ENWL unplanned outages** ([link](https://www.opennetzero.org/electricity-north-west/unplanned-outages1)) | Real, GB distribution | CC BY 4.0 per §10.1; page says "unknown", so confirm | ~313k events, 2000–2026 | Cause, duration, location | ~1 h (register + CSV) | **KEEP: primary training set** |
| **UKPN IIS** (ledger §10.1) | Real, second operator | CC BY 4.0, registration | ~316k events | Restoration stages | ~1 h | **KEEP: cross-operator validation** |
| **NESO 1-s frequency** ([link](https://neso.energy/data-portal/system-frequency-data)) | Real, GB-wide | NESO Open Data Licence | ~2.6M rows/month | None (events from ESO reports) | 15 min | **KEEP: the replayed "sensor stream" + stress context**, not a fault model |

**WEAK (real but slow, narrow or licence-unclear; not for the 18 h build)**
| Dataset | What it is | Why WEAK |
|---|---|---|
| **VSB Power Line Fault Detection** (Kaggle competition; [paper describing it](https://ar5iv.labs.arxiv.org/html/2009.06825)) | Real MV covered-conductor voltage at 40 MHz; 8,712 train signals × 800k samples; 525 positives (partial discharge) | Real and predictive, but it detects **insulation partial discharge**, not outages. It is multi-GB, too heavy for an 8 GB VM in the time, and the competition data licence is unverified (rules page didn't render). The paper's "<0.06%" positive rate is wrong: it's ~6% |
| **LBNL µPMU / Open Power Data** ([portal](https://secpriv.lbl.gov//project/powerdata/); [arXiv 2504.06588](https://arxiv.org/html/2504.06588v1)) | Real µPMU + PQube3 | Open portion = **3 nodes × 3 months, 2015**, LBNL campus. No licence stated. Not a utility outage set |
| **ORNL Grid Event Signature Library (GESL)** ([ORNL news](https://www.ornl.gov/news/check-out-power); [DOE](https://www.energy.gov/node/4837166); IEEE Access 2024, DOI 10.1109/ACCESS.2024.3404886) | Real anonymised voltage/current/frequency event signatures from 12 utilities, labelled taxonomy | Best *real labelled event* source, but it is US, needs registration, and **gesl.ornl.gov returned an error today**. A good roadmap item, too risky to start at hour 0 |
| **NGED "LV Load Monitor Data"** (connecteddata.nationalgrid.co.uk) | Real LV substation monitoring, long format | **Portal returned HTTP 520 twice** (also in §9.2). Voltage attributes unconfirmed |
| **SSEN / UKPN smart-meter LV feeder** ([SSEN](https://opennetzero.org/ssen/smart-meter-lv-feeder-usage); [UKPN](https://opennetzero.org/uk-power-networks/smart-meter-consumption-lv-feeder)) | Half-hourly **consumption** aggregated per LV feeder (≥5 meters) | **No voltage.** Useful only for load context |
| **Hybrid Electrical Fault Detection (Mendeley vc3v6ns6w4)** ([link](https://data.mendeley.com/datasets/vc3v6ns6w4/1)) | 22k rows; two Kaggle sets + synthetic random sinusoids; CC BY 4.0 | Synthetic rows are statistically generated, not physics. Inherits the Kaggle set's simulation. Close to DO NOT USE |

**DO NOT USE (for this build; see 11.8 for refutations)**
- Kaggle `esathyaprakash/electrical-fault-detection-and-classification` **as the "UK fault model"**.
- SERL smart-meter data.
- "LV Network Templates" as an open dataset.

### 11.3 Transfer to Bangladesh / Pakistan (KEEP)
| Claim | Sources | Verdict |
|---|---|---|
| **BD 2026 outages are mainly fuel-shortage load-shedding.** LNG terminal damage left more than half of ~29 GW idle; 3,757 MW unmet (Aug 2026) | [Bonik Barta, 12 Aug 2026](https://en.bonikbarta.com/business/KocAjM18BPzfKGtV/); [Asia News Network, 19 Aug 2026](https://asianews.network/bangladeshs-gas-supply-improves-but-industries-still-struggle/) | KEEP |
| **PK feeder outages are largely policy-driven** (AT&C-loss-based shedding: 12 h 14 min a day on very-high-loss feeders). NEPRA calls this illegal | [Express Tribune, 2 Sep 2026](https://tribune.com.pk/story/2627009/nepra-orders-k-electric-to-end-load-shedding); ledger §9.1 (NEPRA) | KEEP |
| ⇒ A model that detects **equipment faults** from frequency/voltage would miss most BD/PK outage-hours, which are scheduled or shortage-driven. "Just input their frequency and voltage" is **not honest**. Per-grid YAML + local labelled history (PRD §3, PGCB) is the honest path | Synthesis + PRD §3.1/§5.2 | KEEP |

### 11.4 Household view and privacy (KEEP)
- Household smart-meter consumption is **"likely to be personal data"**. Networks may use sub-monthly data only with consent or after Ofgem-approved de-identification. Source: [DESNZ Data Access & Privacy Framework review](https://www.gov.uk/government/publications/smart-metering-implementation-programme-review-of-the-data-access-and-privacy-framework/smart-metering-implementation-programme-review-of-the-data-access-and-privacy-framework); the ICO consultation response (via search: MPAN-linked data is personal data). KEEP.
- Marist ToU §9 already bans real personal data on the VM (ledger §1). So per-home data is **synthetic only**.
- Frequency is the same across a synchronous area (11.1). **A per-home frequency graph shows every home the same line.**

### 11.5 LinuxONE fit (KEEP)
| Claim | Sources | Verdict |
|---|---|---|
| IBM's TF zDNN plugin accelerates **inference**. Training is "on the platform of your choice" | [IBM tutorial](https://www.ibm.com/products/tutorials/accelerating-tensorflow-inference-on-ibm-z16); [zDLC 5.1.0 blog, 29 Jun 2026](https://community.ibm.com/community/user/blogs/sunny-anand/2026/06/29/ibm-z-deep-learning-compiler-510) (inference on Telum II; ONNX in; ships via the IBM Z container registry) | KEEP |
| ⇒ "Trained on LinuxONE" is true **on CPU** (XGBoost/sklearn/small Keras). "Telum accelerates training" is false | The two above | KEEP |
| VM size is **unconfirmed** (the setup-call slide is obscured; nothing official found online). Run `nproc; free -h` before sizing anything | Ledger §1; search found no official spec | WEAK, so verify on the VM |

### 11.6 Community consensus
- **Kaggle fault sets = toy/simulated.** The most-used set (20k downloads, CC0) describes itself as a MATLAB model of four 11 kV generators with faults at the line midpoint, ~12k rows. Papers using Kaggle fault sets report anywhere from ~87% to >99.9% accuracy, and authors of a 2025 IEEE 5-bus dataset note existing sets "don't consider all the practical fault scenarios". A Temple thesis found models trained on simulated PMU data reached only ~77% on field data. Consensus: **fine for learning, not evidence of real-world performance.**
- Reddit and StackExchange are blocked to our fetcher, so no thread-level counts this pass.

### 11.7 Final call (professional + community)
- **Keep** the UK-first idea, but the UK asset is **labelled fault history (ENWL/UKPN)**, not NESO.
- **NESO** = the live/replayed "sensor" stream for system stress (already PRD §5.4).
- **Don't** train the core model on Kaggle simulated faults. A judge with power-systems background will spot it in one question.
- **Transfer** = method + per-grid config + local labels, never "plug in their readings".
- **Household view** = an area/patient status card, not a per-home oscilloscope.

### 11.8 DO NOT USE (quarantined)
| Claim / source | Refuted by | Stripped metric |
|---|---|---|
| "NESO data can detect/locate faults in a system" | NESO portal (no voltage or location fields); NESO frequency explainer; Rydin Gorjão 2020 (bulk behaviour) | — |
| Kaggle `esathyaprakash` fault set as proof a model "works on UK grids" | Its own Kaggle description (MATLAB sim, 4 × 11 kV generators); Samyaktg README; Temple thesis (~77% sim→field) | Any "9x% accuracy" from it |
| SERL as a usable dataset | [serl.ac.uk/researchers](https://serl.ac.uk/researchers/): accredited UK academics only, secure lab, no download, **≥3 months** to access, UG students not eligible; ToU §9 | — |
| "LV Network Templates" (WPD 2011–13) as open voltage data | [WPD project page](https://www.westernpower.co.uk/innovation/projects/network-templates) + search: 500M measurements analysed, but no open-data release found | — |
| "BD/PK outages are faults we can predict from frequency/voltage" | Bonik Barta + ANN (BD fuel shortage); Express Tribune/NEPRA (PK AT&C policy shedding) | — |
| "Telum NNPA trains the model" | IBM TF inference tutorial; zDLC 5.1.0 blog | — |
| Low Carbon London (London Datastore) as voltage data | London Datastore listing: kWh per half-hour only | — |


---

## Realisation pass — making the pivot's features real (2026-10-17)
**Question:** can each feature that was rejected or watered down be built for real? Live feeds were probed with curl at about 19:30 BST today. Every source below was fetched in this pass.

**Headline:** two finds change the picture.
1. **The live DNO feeds already give real fault locations.** UKPN (anonymous access today), Northern Powergrid and SSEN publish postcodes and lat/long. SSEN also gives feeder IDs.
2. **An open, real, household-level voltage + frequency + outage dataset exists for a lower-middle-income grid:** nLine GridWatch Accra. It has 1,300+ plug-in sensors, 2018–2024, a reading every 2 min, and is CC BY-NC 4.0.

Together these make "localise", "real voltage" and "sensors that show the model works" real. A minutes-ahead blackout forecast from frequency is still not real.

**Community input is thin this pass.** Reddit is blocked to our fetcher (as in earlier passes), and HN Algolia returned nothing relevant. What community voice there is comes from practitioner statements inside utility and regulator documents.

### CATEGORY INDEX
- 12.1 Fault localisation: live DNO feeds, real-fault-driven sensor sim, OpenDSS, FNET, smart-meter alerts
- 12.2 Real voltage data: Accra GridWatch, UK-DALE, NGED, PSML, others
- 12.3 Predicting outages before they happen: weather fault risk, BD shortfall, frequency lead time
- 12.4 Other countries, "only government access", "every country"
- 12.5 Household view: privacy and value
- 12.6 Waveform fault datasets
- 12.7 Item 10: "outside 49–51 Hz = blackout" (grid codes, incidents, what frequency can't see)
- 12.8 Corrections to earlier sections
- 12.9 Community consensus
- 12.10 Final call
- 12.11 DO NOT USE (quarantine)

### 12.1 Fault localisation
**Live DNO feeds: what they really expose (probed today)**

| Feed | Endpoint and access | Location fields | Other fields | Licence | Verdict |
|---|---|---|---|---|---|
| **UKPN Live Faults** | `ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-live-faults/records`. **Anonymous; 62 live records** | `fullpostcodedata` (**full unit postcodes**, e.g. N13LD;N13LE…), `postcodesaffected` (sector), `geopoint`, `operatingzone` | `nocustomeraffected`, `powercuttype` (planned/unplanned), `creationdatetime`, `restoreddatetime`, `estimatedrestorationdate`, cause text | **CC BY 4.0** (dataset metadata) | **KEEP.** Upgrades §9.2's WEAK: the login wall applies to the portal UI, not to this API today |
| **Northern Powergrid Live Power Cut Data** | `northernpowergrid.opendatasoft.com/.../live-power-cuts-data/records`. **Anonymous; 105 records** | `postcode[]`, `lat`/`lng`, `area` | `totalconfirmedpowercut` (customers), `natureofoutage`, `loggedtime`, `estimatedtimetillresolution`, `duration` (min), `incidentstatus`, `type` | NPg Open Data Licence v1.0 | **KEEP** |
| **SSEN PowerTrack** | `ssen-powertrack-api.opcld.com/gridiview/reporter/info/livefaults`. **Anonymous; gzip JSON** | `latitude`/`longitude`, bounding box, `affectedAreas`, plus **`primaryNrn`, `hvFeederNrn`, `lvFeederNrn`, `txNrn`** (substation, feeder and transformer IDs) | `affectedCustomerCount`, `priorityCustomerCount`, `loggedAt`, ETR, `engineerOnSiteTime`, `resolved`, LV/HV | Not stated (§9.2 KEEP) | **KEEP** |
| ENWL live | `sp-enw-live-customers-off-supply` | **None.** A count time series only; records return 403 without login | — | CC BY 4.0 | WEAK for localisation |

- **Postcode to lat/long:** the **postcodes.io** bulk API is keyless. Today it returned lat/long, LSOA and district for UKPN and NPg postcodes. It is built on ONS postcode data. KEEP.
- ⇒ **Localising a GB fault to postcode or feeder is real today, and the DNOs do it themselves.** Our job is not to "find" GB faults. It is to say **which enrolled homes sit inside a live fault**, and how long the fault will last against each patient's reserve.

**Real-fault-driven sensor simulation (item 1b): sound, with one honesty rule**
- **Mechanism:**
  - Take each live or historic fault.
  - Place synthetic plug-in sensors in the **affected unit postcodes** (UKPN `fullpostcodedata`, NPg `postcode[]`).
  - Place control sensors in **neighbouring unaffected postcodes** in the same sector.
  - Affected sensors go silent at the real start and come back at the real `restoreddatetime`.
  - The quorum localiser (PRD §5.1) must recover the affected set. It is scored against the DNO's real postcode list.
- **Honesty rule:** if the sensors behave perfectly, the score is circular. So inject documented field imperfections:
  - about 74% fleet uptime, with ≥2 co-reporters required (Klugman IPSN'21, §10.4);
  - random comms dropouts;
  - some sensors behind backup;
  - partial-area outages, per SSEN's live message text: "It is normal to see 1 in 3 homes affected".

  The score then measures *the localiser, under realistic sensor noise, against real fault footprints*. It does not measure sensor physics. Say exactly that.

**Physics simulation on IEEE feeders (item 1c)**

| Claim | Sources | Verdict |
|---|---|---|
| ML fault location from voltage at a few buses on IEEE 34/123-bus feeders is an established, recent, peer-reviewed method | Chanda & Soltani, *IEEE Trans. Power Systems* 2024 ([arXiv 2309.09921](https://arxiv.org/abs/2309.09921)): IEEE-123; detect, locate and classify; sparse-measurement placement. [arXiv 2509.02192](https://arxiv.org/html/2509.02192v1) (2025 preprint): about 94% location accuracy on IEEE-123 and >96% on IEEE-34. [GCN, arXiv 1812.09464](https://arxiv.org/pdf/1812.09464) (older): works with few measured buses | KEEP. The method is real |
| These accuracies don't transfer to field data | §11.6 (Temple thesis: about 77% sim→field). PROTECT-90 authors: public resources are "proprietary simulations or real recordings without structured simulation assumptions" | KEEP, as the caveat |
| **dss_python / OpenDSSDirect.py cannot run on s390x** | PyPI: `dss-python` and `opendssdirect.py` are pure wrappers. The engine, `dss_python_backend`, ships wheels only for x86/x86_64/aarch64/macOS/Windows. [DSS C-API releases](https://github.com/dss-extensions/dss_capi/releases) 0.15.0b4 (Feb 2026) cover only Linux x64/x86/arm64. DSS C-API is Object Pascal, and the [Free Pascal z/Architecture port](https://wiki.freepascal.org/ZSeries) is an unfinished hobby port (last edited 2016; "ain't been implemented") | **KEEP: not on LinuxONE.** Generate data off-box, ship a CSV, then train and infer on the VM |
| pandapower is pure Python (`py3-none-any`, BSD), but v3.5.6 pins `pandas~=2.3`, `scipy>=1.15` and `pandera` | [PyPI JSON](https://pypi.org/pypi/pandapower/json) | WEAK. A clash with the IBM image's pandas is likely; verify |

**FNET/GridEye TDOA (item 1d)**
- **It is real.** UTK/ORNL locate *disturbances* (generator or line trips) by the time difference of arrival of frequency changes. It has a US patent and sends email alerts ([UTK event location](https://powerit.eecs.utk.edu/eventlocation.html); [FNET](https://en.wikipedia.org/wiki/FNET): about 200 North American recorders, ">300 worldwide" as of 2020). The recorders plug into ordinary outlets and report f, V and angle every 100 ms ([OSTI 1771877](https://www.osti.gov/biblio/1771877)).
- **No accuracy figures and no open-data policy were found.** §9.4 already says the data needs authorisation.
- **It locates system-scale disturbances, not feeder or house outages.** A distribution fault doesn't move system frequency (12.7). WEAK. **Roadmap at most, and the wrong tool for homes.**

**Smart-meter "last gasp" (item 1e)**

| Claim | Source | Verdict |
|---|---|---|
| SMETS2 meters send **AD1 Power Outage Alerts** through the DCC to DNOs once an outage passes 3 min. The SEC target is delivery within 60 s; the DCC has admitted its current Comms Hub and network design can't meet it | [Ofgem SEC MP096 decision 2022](https://www.ofgem.gov.uk/sites/default/files/2022-09/SEC%20MP096%20-%20Decision.pdf) plus SEC working-group notes (found via search). [Ofgem SECMP293 decision, Oct 2026](https://www.ofgem.gov.uk/sites/default/files/2026-10/Authority-decision-SECMP293.pdf): AD1 is in the DCC enhanced-availability service, and DNOs said a DCC maintenance window during Storm Darragh disrupted their response | KEEP |
| Real-world quality is poor. WPD received about **75,000 AD1 alerts a month** from about 1.1 M capable meters, and **over 70% were auto-filtered as spurious**. Of the rest, about 5% linked to known incidents; "the vast majority… seem to be false alerts" | [WPD response to the Ofgem DCC review, Apr 2021](https://www.ofgem.gov.uk/sites/default/files/docs/2021/04/2021.04_dcc_review_call_for_evidence_response_wpd.pdf) (text extracted) | KEEP. Dated and from one DNO; SECMP293 shows DNOs still rely on it |
| **No open AD1 data exists.** It goes only to DNOs through the DCC, and it is personal data (MPAN-linked, §11.4) | Nothing open found in SEC or Ofgem documents; §11.4 | KEEP. **Not possible in this build.** The production path is to consume the DNO's aggregate |

### 12.2 Real voltage data (item 2)
**KEEP**

**nLine GridWatch Accra: the smallest usable real voltage + outage source**
- **Sources:** [nLine public data](https://nline.io/public-data/gridwatch); [Climate Change AI blog, 2024](https://www.climatechange.ai/blog/2024-08-29-ghana-power-grid); [Graphic Online, Oct 2024](https://www.graphic.com.gh/business/business-news/groundbreaking-data-on-power-quality-in-ghana.html).
- **What it is:** real plug-in sensors in homes and businesses across 14 Accra districts.
  - Each row: `time, site_id, site_latitude/longitude, voltage, frequency, is_powered, district, region, state_of_charge…`
  - One reading every **2 min**, Jul 2018 to Jul 2024. nLine's page says "to Jul 2023", but the bucket holds files up to 2024-06-30.
- **Licence and access:** **CC BY-NC 4.0** (nLine page).
  - The official route is a request form, which issues an API key.
  - The bucket `storage.googleapis.com/nline-public-data/ghana/gridwatch_data/csv/` is also readable anonymously (checked).
- **Size:** about 10 MB a day in 2018, 24 MB a day in 2021 and 190 MB a day in 2024.
- **Profile of 2021-06-01:**
  - 84,623 rows from 390 sites in 21 districts;
  - 14.7% of rows are unpowered;
  - powered voltage: 1st percentile 190 V, median 235 V, 99th percentile 260 V;
  - **2.5% of powered readings are below 200 V**;
  - frequency, 1st to 99th percentile: 50.06–50.27 Hz.
- ⚠ **Treat site GPS as personal data.** It has 5–7 decimal places. Coarsen it off-box before it reaches the VM (ToU §9).

**Other KEEP rows**
- **Plug-in sensors find what utilities miss:** [Klugman et al., IPSN 2021](https://web.eecs.umich.edu/~prabal/pubs/papers/klugman21watching.pdf) (462 sensors; about twice the outages the utility recorded); [CEGA GridWatch](https://cega.berkeley.edu/research/gridwatch); [MCC blog](https://www.mcc.gov/blog/entry/blog-053123-data-monitor-power-outages/).
- **Ghana fits the country filter.** The World Bank API today classes Ghana as lower-middle income, and 73.8% of firms report outages (2023).

**WEAK**
- **UK-DALE** ([UKERC EDC record](https://data.ukedc.rl.ac.uk/browse/edc/efficiency/residential/EnergyConsumption/Domestic/UK-DALE-2015/ReadMe_DALE.html), via search):
  - 16 kHz whole-house V and I for **3 houses**, as FLAC files;
  - **uncalibrated**, with calibration files supplied;
  - CC BY 4.0; total size not found.

  These are UK homes with stable mains, so there are few sags to learn from. It is the wrong voltage regime for a brownout detector.
- **NGED "LV Load Monitor Data"** ([CKAN](https://connecteddata.nationalgrid.co.uk/api/3/action/package_show?id=lv-load-monitor-data)):
  - now reachable (it returned HTTP 520 before);
  - 301 substation CSVs, "Near Real Time", WPD Open Data Licence;
  - `datastore_search` returned **403 "restricted to registered users"**;
  - voltage columns unconfirmed.
- **Northern Powergrid primary/BSP operational metering:** active power in **kW**, not voltage. Records need a login.
- **PSML** ([Zenodo](https://zenodo.org/records/5130612); [Scientific Data 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9214688/)): CC BY 4.0, 5.2 GB, but **simulated** (a transmission + distribution co-simulation).
- **Unchanged:** LBNL µPMU, Low Carbon London and SSEN/UKPN LV feeder consumption (§11.2, §11.8).

### 12.3 Predicting outages before they happen (item 3)
**3a. Weather-driven area fault risk: an established method with a UK precedent**

| Claim | Sources | Verdict |
|---|---|---|
| Probabilistic day-ahead (up to 4-day) forecasts of **district-day fault counts** from weather work on GB distribution networks. **Setup:** SPEN, districts of about 1,000 km², trained on ERA5 with ECMWF ENS forecasts. **Inputs:** wind, gusts, temperature, precipitation, CAPE, tree-in-leaf. **Trial:** with SPEN engineers, Oct 2024 to Mar 2025; "sufficiently reliable to inform decision-making". **Limits:** circuit level judged infeasible; fault data not public | [Maia, Castro-Camilo, Browell (Glasgow), arXiv 2603.01653, Mar 2026](https://arxiv.org/html/2603.01653v1). A preprint whose skill appears only in figures | KEEP for the method; WEAK for any quotable skill number |
| Weather-related faults at a substation can be predicted from meteorological observations alone (5 years of UK DNO data, HV and LV) | [Tsioumpri, Stephen, McArthur, *Energies* 2021](https://ideas.repec.org/a/gam/jeners/v14y2021i8p2053-d531906.html) | KEEP. Corroborates the above; dated |
| Most weather-outage models were built and validated on a few US utilities, so they transfer poorly | [Arora & Ceferino, NHESS 2023](https://nhess.copernicus.org/articles/23/1665/2023/); [hurricane review, Eng. Appl. AI 2024](https://research.uaeu.ac.ae/en/publications/machine-learning-for-power-outage-prediction-during-hurricanes-an/) | KEEP, as the caveat |
| **Open-Meteo** is usable without a key. **Endpoints:** the archive API (`archive-api.open-meteo.com/v1/archive`: ERA5 from 1940, ERA5-Land from 1950; daily max gust, precipitation, temperature) and a forecast API for tomorrow. **Terms:** CC BY 4.0; free non-commercial use up to 10k calls a day, 5k an hour and 600 a minute. **Tested today:** Manchester on 2024-01-01 showed gusts of 55.1 km/h, and a forecast for 2026-10-18 came back. **Gaps:** no lightning variable. **Install:** plain JSON, so no pip package is needed | [Open-Meteo terms](https://open-meteo.com/en/terms); [historical API docs](https://open-meteo.com/en/docs/historical-weather-api) | KEEP |
| The ENWL historic outages metadata, checked today, confirms the fields: `incident_date_time`, `restoration_date_time`, `direct_cause_category`, `direct_cause`, `district_name`, `primary_substation`, `local_authority`, `geometry`, `voltage`, `customer_affected`, `exceptional_event_id`. There are **312,936 records under CC BY 4.0**; reading the records needs a login | ODS catalog API; §10.1 | KEEP |

- ⇒ **Honest build:** predict P(≥k faults in ENWL district d tomorrow).
  - **Inputs:** ERA5 daily weather (Open-Meteo), season and the district's base rate.
  - **Model:** XGBoost with a Poisson objective.
  - **Evaluation:** Brier score and Brier skill score against district climatology, on a time split.
  - **Live:** the Open-Meteo forecast for tomorrow.
  - **Claim:** "replicates a published GB method on open data". Never claim "predicts your outage".

**3b. Bangladesh day-ahead load-shedding**
- **Data:** PGCB hourly has demand, generation and load-shedding (§10.1).
- **Prior work:**
  - Demand forecasting on it is common: [Springer 2025](https://link.springer.com/article/10.1007/s42488-025-00140-9) (MAPE 2.3%); [MDPI 2024](https://www.mdpi.com/2504-2289/8/2/12).
  - A load-shedding classifier exists only in one 2026 conference paper ([VU Bangladesh](https://vu.edu.bd/publications/3168/an-intelligent-machine-learning-based-load-shedding-prediction-and-smart-energy-management-framework-for-power-grid-optimization-in-bangladesh)). WEAK.
- **The bar is persistence.** The 2026 driver is fuel supply, which is exogenous (§11.3), so a forecast must beat "tomorrow = today".
- **Validation data:** PGCB ends in Mar 2026, so live checks rely on the BPDB daily PDFs.
- **Verdict:** WEAK as a headline; fine as a backtest.

**3c. Minutes-ahead warning from frequency/RoCoF: not real** (details in 12.7)
- On 9 Aug 2019, GB went from 50 Hz to the 48.8 Hz LFDD in about 1.5 min.
- Elexon's live data is 15 s resolution with about 1.5 min lag (§9.4). A live "warning" built on it arrives **after** LFDD.
- So this works only as a replay on NESO's 1-s data, with seconds of lead time.

### 12.4 Other countries, "only government access", "every country" (items 4–6)
**Sensors can generate the missing labels (verified).** nLine's Accra network built a 6-year, household-level outage and voltage dataset that the utility lacked, and it counted about twice as many outages as the utility (12.2). This is precedent for our approach. Cite it; don't claim it as ours.

**The minimum a new grid must supply:**
1. A `grid.yaml` built from its grid code: nominal Hz and V, the protection ladder, timezone, weekend and seasons (PRD §3.1).
2. Either a seed outage history or a few weeks of sensor data, with 2–3 anchor sensors per cluster.
3. Any load-shedding schedule or daily shed figures.
4. A health-authority partner that holds the consented patient register.

Recalibration is PRD M6 (isotonic, per region) as local labels arrive.

**"Only government API access stops us" is false as stated.** What deployment really needs:
- data-sharing agreements with the grid operator;
- a consented register under the health authority (BD PDP law: consent and a DPIA; §9.6);
- a funded sensor fleet (hardware and SIMs, at about 74% uptime);
- telco SMS and voice integration;
- DHIS2 integration;
- clinical governance and a prospective pilot.

**Judge-safe line:** *"The software runs on open data today. Deployment needs three agreements (grid-operator data, a health-authority register and a sensor pilot), not new science."*

**"Every country": drop it.** The honest scaling statement is *any synchronous area, via config plus local labels*.
- **666 M people have no electricity at all** (2023; [Tracking SDG7 2025](https://www.irena.org/Publications/2025/Jun/Tracking-SDG-7-The-Energy-Progress-Report-2025); [UN](https://www.un.org/en/node/208821)). KEEP the figure, but these people are **not our market**: they have no grid, so they have no outages.
- **"Unreliable supply" counts are WEAK.**
  - The Rockefeller Foundation map says "1,456 M", built from a crude firm-share method. It cites 789 M without access, which dates it to about 2020.
  - A World Bank document says "up to a billion" and is undated.
- **Use these instead** (KEEP; World Bank API today):

  | Country | Population (2025) | Firms reporting outages |
  |---|---|---|
  | Bangladesh | 175.7 M | 71.4% |
  | Pakistan | 255.2 M | 50.7% |
  | Ghana | 35.1 M | 73.8% |

### 12.5 Household view (item 7)
**Privacy holds up.**
- A data subject has a right of access to their own personal data ([UK GDPR Art. 15](https://www.legislation.gov.uk/eur/2016/679/article/15)).
- The k≥11 rule governs data released to others, such as maps and utilities. It does not stop someone seeing their own data.
- Art. 15(4) says a copy must not adversely affect the rights of others. So the view never shows neighbouring homes, and it can't be queried by map cell or by coordinate. KEEP.

**Frequency is the same line for everyone** across a synchronous area (12.7). Label it "grid health (same for everyone)", not "your frequency".

**The value is real.** In Accra, 2.5% of powered readings fall below 200 V on an ordinary day. Each device's minimum operating voltage must come from its datasheet; it is not verified here, so quote no numbers.

On the VM, use synthetic or Accra-replay readings only (ToU §9).

### 12.6 Waveform fault datasets (item 9)
**No real, open, labelled distribution-fault waveform set usable in 16 h was found.** All candidates are WEAK:
- [PROTECT-90](https://cris.fau.de/publications/365580344?lang=en_GB): simulated, 90 kV, 12.5 GB.
- VSB: about partial discharge, not faults.
- [IEEE DataPort, real distribution circuit](https://ieee-dataport.org/keywords/voltage-and-current-waveforms): has no fault labels.
- [HF-CT-Fault](https://ieee-dataport.org/documents/hf-ct-fault-high-frequency-current-transformer-fault-archive-ratiophase-error-metrics): provenance unclear.

An IEEE-feeder dataset generated off-box is defensible only if it is labelled "physics-simulated". Even then it doesn't feed the triage decision. Roadmap.

### 12.7 Item 10: "outside about 49–51 Hz signals a cascading blackout"
**Grid-code thresholds (KEEP)**

| Grid | Threshold line | Source |
|---|---|---|
| GB | Statutory ±1% (49.5–50.5 Hz), which may be exceeded for ≤60 s after a large loss. In practice the deviation is held to −0.8 Hz. **LFDD starts at 48.8 Hz** (5% of demand); the final level is 48.0 Hz (50% cumulative) | [NC ER Annex (GB values)](https://www.legislation.gov.uk/eur/2017/2196/annex); [MacIver, Bell, Nedd, EPSR 2021](https://strathprints.strath.ac.uk/77056/1/MacIver_etal_EPSR_2021_An_analysis_of_the_August_9th_2019_GB_transmission_system.pdf); [UKERC](https://ukerc.ac.uk/news/what-happened-electricity-system-fri-aug-9-2019/) (Grid Code practical lower limit: 47.5 Hz) |
| Continental Europe | **LFDD starts at 49.0 Hz** (5%); the final level is 48.0 Hz (45% cumulative) | NC ER draft annex (via search) and the [Elia LFDD deck, 2024](https://www.elia.be/-/media/project/elia/elia-site/electricity-market-and-system/emergency-situations/20240402_lfdd_infosessionforindustry_en.pdf) ("first load-shedding at f = 49,0 Hz") |
| Bangladesh | Operator ladder at 49.5 / 49.3 / 49.1 Hz; UFLS at 48.9 / 48.8 / 48.7 Hz | §10.3 |
| Pakistan | Sensitive band 49.8–50.2; tolerance 49.5–50.5; contingency 49.3. ⚠ UFLS stage values not found | §10.3 |

**Real events (KEEP)**
- **GB, 9 Aug 2019:** frequency fell from 50 to 48.8 Hz and LFDD fired "for the 1st time in eleven years". About 1.1 M customers were cut, but there was **no blackout**, and all demand was back by 18:30. RoCoF and vector-shift protection on embedded generation **added** at least 580 MW of losses (MacIver; UKERC; §9.4).
- **Iberia, 28 Apr 2025: over-voltage came first.**
  - After 12:32:57 a transformer tripped on over-voltage protection on its 220 kV side.
  - Renewables tripped between 12:33:17 and 12:33:18.
  - Voltage rose sharply from 12:33:18 to 12:33:21, and frequency fell only in those last seconds.
  - Synchronism was lost from 12:33:19.
  - Automatic load shedding activated, by 12:33:23, but could not prevent the collapse.

  Sources: [Renewable Energy World](https://www.renewableenergyworld.com/power-grid/report-reveals-timeline-of-iberia-blackout-catastrophe/); [pv magazine on the ENTSO-E final report](https://www.pv-magazine.com/2026/03/23/entso-e-report-finds-systemic-failures-behind-2025-iberian-blackout/); [FAU, May 2025](https://www.ees.tf.fau.de/files/2025/05/Blackout_ES_PT_FR_28_04_2025_en.pdf).
- **Pakistan, 23 Jan 2023:** the first recorded excursion was over-frequency to 50.75 Hz, inside a ±1 Hz band (§9.4).
- **Bangladesh, 2014:** frequency fell from 50.33 to 48.65 Hz in 6.8 s, and the country was dark in about 59 s.
- **Bangladesh, 2022:** the PGCB probe blamed transmission tripping and overload ([Dhaka Tribune](https://www.dhakatribune.com/bangladesh/277793/nasrul-initial-probe-suggests-under-frequency); [Financial Express](https://old.thefinancialexpress.com.bd/national/two-pgcb-engineers-suspended-over-national-grid-failure-1665911837)).

**What frequency can see at all (KEEP)**
- **Frequency is one shared signal.** "All customers experience a common frequency" ([Ofgem 1998/99 performance report](https://ofgem.gov.uk/sites/default/files/docs/2000/01/report-on-distribution-and-transmission-system-performance-1998-99-2501_0.pdf), text extracted). Rydin Gorjão 2020 and the NESO explainer agree (§9.4, §11.1).
- **Most interruptions start on the distribution network.** The same Ofgem report says generation failures are "extremely small", transmission's contribution is "minor", and "distribution systems are by far the most significant determinant". The report is dated. RIIO-ED2 still reports interruptions by source and voltage ([Annex F](https://www.ofgem.gov.uk/sites/default/files/2025-02/RIIO-ED2-Annex-F-Interruptions-v1.1.pdf)).
- **Quantified on open data:**
  - ENWL alone logged 312,936 unplanned distribution incidents in 2000–2026, about 12k a year, and it is one of 14 GB licence areas.
  - GB LFDD fired only in 2008 and 2019.
  - No recent GB percentage split by source was found. The circulating "~90%" figure is quarantined (12.11).
- **In Bangladesh and Pakistan, most outage-hours are operator load-shedding.** Its causes are fuel shortage in BD and loss-based policy in PK (§11.3). Shedding is how operators *keep* frequency in band, so a frequency rule sees none of it.
- **RoCoF reacts earlier than the size of the deviation.** It is used operationally as a warning signal: in Yunnan, >0.4 Hz/s means warning and >0.5 Hz/s means insecure ([arXiv 2509.07320](https://arxiv.org/pdf/2509.07320); see also [Imperial's work on nadir prediction](https://spiral.imperial.ac.uk/entities/publication/fb3b3d5c-2201-4389-b841-7fb3d4825abd)). It needs data at 1 s or faster, and the lead time is still only seconds.

**Detecting a local or house blackout: the real alternatives**

| Signal | Resolution | Latency | Open? | Fit for GB | Fit for BD/PK |
|---|---|---|---|---|---|
| DNO live fault feeds | Postcode or feeder | Minutes | Yes (12.1) | **Best** | None (no open feeds) |
| Smart-meter AD1 alerts | One meter | ≥3 min + 60 s (target not met) | No | Production path, through the DNO | No DCC equivalent |
| Plug-in sensors (nLine) | One home or site | 2 min | Accra history yes; live no | Pilot only | **Best** |
| IODA (internet outages) | Region (BD: divisions, checked today) | 5–10 min | Yes, keyless | Large events only | Large events (§9.3) |
| Black Marble VNP46A2 (night lights) | 500 m | Daily; latency undocumented | Yes ([NASA](https://viirsland.gsfc.nasa.gov/Products/NASA/BlackMarble.html)) | Poor | Poor in monsoon |
| Utility SCADA / AMI | Feeder or meter | Seconds to minutes | No; needs an agreement | Through the DNO | Through an MoU |
| Social media / OSINT | Area | Minutes to hours | Partly | Noisy | Noisy |

**The layering (item 10d): confirmed, with one correction**
- **System layer:** a rule, not a trained classifier. GB has had only 2 LFDD events since 2008, which is too few labels to train on. Validate on the 2019 replay and on false alarms per month.
- **Local layer:** ENWL/UKPN fault history plus weather, giving district-day fault risk.
- **Duration layer:** survival models.
- **Correction:** add an explicit **detection layer** (DNO feed, sensor quorum, IODA). Detection is not prediction.
- **For Bangladesh,** the local prediction layer is the PGCB shedding model, not weather.

### 12.8 Corrections to earlier sections
- **§9.2:** UKPN was marked WEAK; it is **KEEP** today (anonymous API, CC BY 4.0, full postcodes).
- **§11.1/§11.2:** the ENWL licence was "unknown". The ODS metadata says **CC BY 4.0**; reading the records still needs a login.
- **§11.2:** the NGED portal returned HTTP 520. It is reachable today, but its LV monitor data is for registered users only.
- **§11.4:** a per-home *voltage* view of the household's own data is fine (12.5). A per-home *frequency* view still shows everyone the same line.

### 12.9 Community consensus
- Reddit is blocked, and HN had nothing relevant.
- The practitioner voices that exist agree with each other:
  - WPD: smart-meter alerts are "not proving as beneficial as first thought".
  - SPEN engineers: weather-driven fault forecasts are useful for situational awareness.
  - The sim-to-field gap is real (§11.6).
- Combined call: the DNO owns location truth; prediction works at district-day level; ML trained on simulated faults doesn't transfer.

### 12.10 Final call
**Build:**
- live DNO localisation from UKPN, NPg and SSEN;
- the real-fault-driven sensor simulation, with noise injected, scored against real postcodes;
- an **Accra GridWatch replay** as the real-sensor proof (outage quorum plus brownout detection);
- an own-home view;
- optionally, ENWL × Open-Meteo district-day fault risk.

**Don't build:** OpenDSS on LinuxONE, FNET, smart-meter alerts, waveform classifiers, or "minutes-ahead" frequency warnings.

**Frequency** stays a system-stress context signal, as PRD v2 already says.

### 12.11 DO NOT USE (quarantined)
| Claim | Refuted by | Stripped metric |
|---|---|---|
| "Outside 49–51 Hz means a cascading blackout; frequency alone tells us one is coming" | GB 2019 (LFDD at 48.8 Hz, no blackout); Iberia 2025 (over-voltage first); PK 2023 (started inside ±1 Hz); NC ER and Elia (49.0 Hz is when defence is already firing); Ofgem (one common frequency; distribution dominates) | "±1 Hz" as a predictor |
| "Frequency/RoCoF gives minutes of warning" | MacIver 2021 (about 1.5 min from first loss to LFDD); Elexon lag (§9.4) | Minutes of lead time |
| "OpenDSS runs on LinuxONE" | PyPI wheels; DSS C-API release assets; Free Pascal's ZSeries page | — |
| "We can use smart-meter last-gasp data" | No open data; DNO-only; personal data; WPD: >70% spurious | — |
| "~90% of interruptions originate in distribution" | No primary source found (repeated only in textbooks and vendor pages) | 90% |
| "1.46 B people have unreliable power" as a headline | Crude method, about 2020; World Bank figure undated | 1,456 M |
| "666 M without electricity" as our market | They have no grid, so no outages to triage | 666 M |
| PSML as "real PMU data" | It is a co-simulation (Zenodo; Scientific Data) | — |

---

## Country + dataset pass — free-healthcare outage grids (2026-10-17)
**Question:** which 2–3 grids have frequent blackouts **and** free or universal public healthcare, plus open data we can use tonight? GB stays the proving ground.
**Method:** about 40 web calls, ~21:20–22:30 BST. Every source below was fetched (World Bank API, Kaggle API, IODA API, GCS bucket and PDFs via curl + pdftotext). Nothing that §9–§12 already settled was re-researched.
**Community input:** Reddit is still blocked to our fetcher (§11–§12), so it wasn't retried. The only community signal here is Kaggle download counts.

**Headline**
- **Only Ghana passes all three filters cleanly.**
- **Sri Lanka** has free public care by policy, but its out-of-pocket (OOP) share is **54.8%**, as bad as Pakistan's.
- **South Africa** has the best healthcare number (OOP 6.7%), but **no load-shedding for 504+ days** (§9.9 already said so; reconfirmed below).
- The honest pitch is therefore: **Ghana = lead target. Sri Lanka = national-collapse case. South Africa = load-shedding stage mechanics with the best history.**

### CATEGORY INDEX
- 13.1 Country scorecard
- 13.2 Per-country evidence
- 13.3 Per-grid YAML constants (verified)
- 13.4 Datasets found this pass
- 13.5 Localisation: new bits only
- 13.6 Final call
- 13.7 Source ledger (KEEP → WEAK → DO NOT USE)

### 13.1 Country scorecard
OOP = out-of-pocket share of current health spending, World Bank WDI `SH.XPD.OOPC.CH.ZS`, 2023, pulled live tonight. Firms = `IC.ELC.OUTG.ZS`, latest non-empty year.

| Country | (a) Outages 2024–26 | (b) Healthcare + OOP | (c) Open data tonight | Verdict |
|---|---|---|---|---|
| **Ghana** | Firms 73.8% (2023). Dumsor in Mar–Apr 2024, with GRIDCo citing AFLS relay trips. Widespread outages in Apr 2026 (Akosombo substation fire plus faults) | **NHIS**, plus **Free Primary Healthcare** launched Apr 2026 (150 districts; nationwide 2027–28). **OOP 26.7%** | **nLine GridWatch**: real household V, f and is_powered every 2 min, 2018 to Jun 2024, covering the 2024 dumsor (checked: `2024-03-21.csv` exists). IODA has 10 regions | **#1** |
| **Sri Lanka** | Up to 13 h/day of cuts (Mar 2022). National blackout Dec 2023 (>3 h). **National collapse 9 Feb 2025: 4.5 h, then 4 days of rotational cuts, 10.1 GWh unserved.** Firms 38.1% (2025). No 2026 cuts found | Free at public point of use, but **OOP 54.8%** | No open outage-event data. PUCSL PDFs (grid code and incident report). IODA shows the 2025 collapse in the raw signal only (13.5) | **#2** (on grid evidence; fails the OOP test) |
| **South Africa** | 205 days of load-shedding in 2022 and 332 in 2023 (record). **None since 16 May 2025** (504 days at 4 Oct 2026). "Load reduction" still hits 202,590 customers (2.8%) | Free public primary care. **OOP 6.7%** (best) | Eskom Data Portal (hourly; licence unstated). *Data* journal 2026 dataset (CC BY 4.0, Jul 2018–Jun 2023 hourly). eskom-calendar schedules (CC BY-NC-SA, archived) | **#3**: history and mechanics, not current blackouts |
| Bangladesh (baseline) | Severe (§9.1) | OOP 79.3% | PGCB, BPDB (§10.1) | Baseline only |
| Pakistan (baseline) | Severe (§9.1) | OOP 52.9% | Constants only | Baseline only |
| Nigeria | Firms 82.5% (2025) | **OOP 71.9%** | Not checked | Out: fails healthcare |
| Zambia | Firms 89.6% (2025). §9.9: no load-shedding in 2026 | OOP 10.3% | Not checked this pass | Possible alternate; unresearched |
| Ecuador | Firms 74.8% (2024) | OOP 30.9% | Not checked | Not better than Ghana |
| Lebanon, Cuba | — | — | — | Excluded (political or sanction-sensitive) |

### 13.2 Per-country evidence
**Ghana**
- **Healthcare.** The Free Primary Healthcare policy covers CHPS compounds, polyclinic public-health units, community pharmacies, kiosks and outreach. It "complements, not replaces" NHIS. Dialysis goes into a third tier, the Ghana Medical Trust Fund ("Mahama Cares"). Sources: NHIS.gov.gh; Starr FM/Ecofin. KEEP.
- **2024 dumsor.** GRIDCo wrote to the Energy Minister (28 Mar 2024) that ECG ignored load-management directives, which tripped the Automatic Frequency Load Shedding (AFLS) relays. GRIDCo also said ECG had issued no timetable (Citi Newsroom, 4 Apr 2024). Search snippets give 49.47 Hz (21 Mar) and 49.29 Hz (20 Mar); the fetched article itself gives no Hz values, so those numbers are WEAK.
- **2026.** On 26 Apr there was a fire at GRIDCo's Akosombo substation plus network faults; ECG said it was "battling widespread outages" (Yen, 27 Apr 2026). 3News ran a "6-h A/B/C rotation, 800 MW deficit" tool for 25 Apr–1 May 2026. That tool is not official, and the government framed the cuts as technical works, so the 800 MW figure is WEAK.
- **Brownouts are the Ghana story.** The Kleinman Center (Mar 2024) used GridWatch data and found:
  - mean voltage about 219 V against 230 V nominal;
  - 10–20% below nominal about 17% of the time;
  - **43 events a month below 200 V for at least 2 min.**

  This corroborates §12.2 (2.5% of powered readings below 200 V). KEEP.

**Sri Lanka**
- **The PUCSL deck at ACEF 2026 is the official account of 9 Feb 2025.** It is by PUCSL's Director of Licensing and cites the PUCSL investigation report.
  - 11:13:39: a 33 kV bus fault at Panadura, causing a 40% voltage dip at 132 kV.
  - The fault cleared in 1.1 s, but frequency still slid from 50.12 to 49.5 Hz in 5.5 s.
  - **All 5 UFLS stages fired and failed.**
  - Collapse came at 40 Hz after 22 s.
  - Causes: rooftop PV tripping (an extra 77 MW lost in the voltage dip), and a UFLS scheme last updated in 2018 that is blind to more than 1 GW of rooftop PV.
  - Verdict: KEEP. This is another "frequency is not the first signal" case, alongside Iberia (§12.7).
- **2022.** PUCSL approved a 13-h cut for one day (31 Mar 2022) and 8.5 h for 2 Apr (FT.lk, plus National Herald). "13 h a day" was the **peak**, not the norm. KEEP, with that wording.

**South Africa**
- **The streak.** SAnews (4 Oct 2026): 504 consecutive days without load-shedding, counted from 16 May 2025. Unplanned outages improved 6.69% year on year. Load reduction is down from 1.69 M to 202,590 customers. Corroborated by SAnews (Aug 2026) and IOL (Jun 2026). KEEP.
- **History.**
  - 2022: 3,751 h (CSIR) vs 3,767 h (Eskom), so the hour count is corroborated.
  - 2023: 332 days (EskomSePush + The Outlier, via IOL), WEAK as a single compiler. CSIR counted 2,896 h by mid-May 2023.
- **Stages.** NRS 048-9 Edition 3 extends load-shedding to **stage 16**, in 16 blocks of about 6.25% of demand. Edition 2 (2019) went to stage 8. Sources: BusinessTech; Polity/Creamer. KEEP.

### 13.3 Per-grid YAML constants (verified)
| Field | Ghana | Sri Lanka | South Africa |
|---|---|---|---|
| `nominal_hz` | 50 | 50 (PUCSL Outlook 2015: **50 Hz ±0.5%**) | 50 |
| `nominal_v` / band | **230 V ±10%** (PURC rule, via the Kleinman Center 2024) | **230 V ±6%** (PUCSL Outlook 2015) | 230 V. ⚠ The ±10% (NRS 048-2) was **not verified**; the primary source wasn't reachable |
| Frequency ladder | AFLS exists (Grid Code 2009 table of contents; GRIDCo 2024). ⚠ **Settings not verified**: the grid-code PDF is behind Cloudflare. Reported operating events 49.47 / 49.29 Hz (WEAK). One press report says UFLS "keeps f above 49.5" (WEAK) | **UFLS (CEB, Dec 2015, PUCSL 2016 study):** 48.75 Hz +100 ms, 7.5% · 48.50 +500 ms, 7.5% · 48.25 +500 ms, 11% · 48.00 +500 ms, 11% · 47.5 instantaneous, 10%. Plus a df/dt stage: **49.0 Hz AND df/dt < −0.85 Hz/s**. Reconnect at 51 Hz +500 ms. The scheme was "last updated 2018" (PUCSL 2026), so the stage values may have shifted. Inverter UF trip prescribed at **47 Hz** | ⚠ UFLS settings **not verified**. The 49.5–50.5 Hz "±1%" band is from press quoting Eskom's MTSAO (WEAK). The SA frequency study (Rydin Gorjão & Maritz 2022/23) used **15-min** data only |
| Load-shedding model | Rotation groups A/B/C, 6 h (3News 2026, WEAK). ECG timetables are ad hoc | Rotational lettered groups (2022 PUCSL approvals: "areas A, B, C…"). 4 days of rotation after the 2025 collapse | **Stages 1–16** (NRS 048-9 Ed. 3); 16 blocks of about 6.25% of demand |
| Timezone / weekend | `Africa/Accra` (UTC+0, no DST) / Sat–Sun | `Asia/Colombo` (UTC+5:30) / Sat–Sun | `Africa/Johannesburg` (UTC+2) / Sat–Sun |
| Fragility notes | Brownouts are chronic (43 events/month below 200 V) | Low inertia; rooftop PV is invisible to UFLS; 22 s from fault to collapse | No national load-shedding since May 2025; local "load reduction" plus municipal faults remain |

Timezone and weekend values are IANA conventions and were not web-checked. They are low-stakes.

### 13.4 Datasets found this pass
**Kaggle check:** the public API (`/api/v1/datasets/list`) works without a key. That is how the provenance checks below were done.

| Role | Dataset | Provenance | Licence | Size / span / resolution | Verdict |
|---|---|---|---|---|---|
| Real household V/f/outage (Ghana) | nLine GridWatch, `storage.googleapis.com/nline-public-data/ghana/gridwatch_data/csv/` | Academic and industry (Berkeley/nLine); peer-reviewed use (IPSN'21, Kleinman 2024) | CC BY-NC 4.0 (§12.2) | 2018-07 → 2024-06, 2 min, **covers the 2024 dumsor** (checked). Columns include `respondent_id`, GPS, `is_powered`, `voltage`, `frequency` | **KEEP** (already §12; the new fact is the 2024 coverage) |
| SA load-shedding plus system hourly | *Data* (MDPI) 11(6):149, Tshuma, Ranganai, Sivhugwana, **18 Jun 2026**, DOI 10.3390/data11060149 | Academic; built from the Eskom Data Portal | Article CC BY 4.0 (Crossref). **Repository and data licence not seen**: MDPI returned 403 | Hourly, Jul 2018–Jun 2023; LS frequency, demand, generation, imports, PCLF/UCLF | **WEAK** until the data link is found |
| SA official system data | Eskom Data Portal (`eskom.co.za/dataportal`) | Official | **Not stated**; footer "All rights reserved" | Hourly; includes "manual load reduction"; request form, up to 5 years per request | **WEAK** (licence); fine for internal analysis with attribution |
| SA schedules by area | `beyarkay/eskom-calendar` (GitHub) | Community, from Eskom posts on X | Code GPL-3.0; **data CC BY-NC-SA 4.0** | `machine_friendly.csv` (area, stage, start, end, source). **Archived**: "loadshedding seems to have stopped" | **KEEP** for area-level SA history (NC-SA must be noted in the README) |
| SA live area status | EskomSePush API | Commercial (WELLWELLWELL) | API licence (1 Aug 2022): personal, internal or research use; **free tier = your home residence only; no third-party sharing** | Live | **DO NOT USE** for a public demo |
| Sri Lanka 2025 collapse timeline | PUCSL ACEF 2026 deck + PUCSL 2016 UFLS study | Official regulator | Public documents | Event-level; second-by-second narrative | **KEEP** (constants and replay script) |
| Sri Lanka collapse signal | IODA `signals/raw/country/LK`, `ping-slash24` | Academic (Georgia Tech) | Free; "All rights reserved" | 10 min; dip from about 610 → 501 (−18%) between 06:00 and 11:00 UTC on 9 Feb 2025 | **KEEP** as a label; see 13.5 |
| SA household survey item | DataFirst (UCT), e.g. Community Survey 2016 "interruption in past 3 months" | Official (Stats SA) via an academic archive | DataFirst terms (registration) | Survey, not a time series | **WEAK** (prevalence context only) |
| SA frequency | Rydin Gorjão & Maritz (arXiv 2211.05582) | Academic | Paper CC BY 4.0; **data not published** | 2021, 15 min (f, fmin, fmax) | **WEAK**: no open data |
| Medical-device prevalence | No new source found this pass. HHS emPOWER (US) is still the only one (§10.4) | — | — | — | — |

**DO NOT USE (Kaggle)**
- `sbonelondhlazi/sa-electricity-historical-data`:
  - It is labelled **CC0**, but its own description says it is Eskom portal data (Apr 2018–Jul 2022) plus **EskomSePush history** "sourced from a private website". The ESP licence bars redistribution, so the **licence has been rewritten**.
  - 1,463 downloads, so it is widely reused anyway.
- `isuranga/load-forecasting-dataset` ("Sri Lanka national load", Jan 2020–May 2025, 15 min, Apache-2.0): no provenance is stated, national demand is given in kW, and the file is named `_corrected`. Unverifiable.
- `mdeconozzamanecon/load-shedding-problem` (uploaded Sep 2026, Apache-2.0): a Bangladesh daily demand and generation re-upload. It is the same class as the §10.1 Kaggle PGCB/BPDB re-uploads with rewritten licences.
- `musokefrancia/synthetic-power-outage-dataset`: synthetic, by its own title.
- No Kaggle dataset exists for "dumsor" or Ghana outages (the search returned zero).

### 13.5 Localisation: new bits only
- **IODA's `outages/events` returned nothing for Sri Lanka on 9 Feb 2025, but the raw signal clearly dips.** Rule: **run our own detector on `signals/raw`** (active probing, drop below 0.85× the 24-h median), not on IODA's curated events. Add this to the §9.3 rules.
- **IODA covers Ghana in 10 admin-1 regions** (Greater Accra, Ashanti, etc.), so Ghana gets region-level "where", like BD/PK.
- **SA area-level "where" exists historically.** eskom-calendar gives area × stage × start/end, which is enough to replay "which homes were in a shed block".
- The live EskomSePush route is closed by licence (13.4).

### 13.6 Final call
- **Targets:**
  - **Ghana (lead):** clean on all three filters, with real household sensor data covering a dumsor year.
  - **Sri Lanka (#2):** a recent national collapse with a published second-by-second timeline and verified UFLS settings. Be explicit that OOP is 54.8%.
  - **South Africa (#3, history and mechanics):** the best health-cost profile and a staged load-shedding model. Say plainly that load-shedding stopped in May 2025.
- **GB** stays the live proving ground.
- **BD/PK** drop to "the same method applies" baselines.
- **Don't** claim "free healthcare" for Sri Lanka without the OOP caveat.
- **Don't** claim ongoing SA load-shedding.
- **Don't** use EskomSePush, or any Kaggle re-upload of it.

### 13.7 Source ledger
**KEEP**
- World Bank WDI API (OOP; firms reporting outages), fetched live. Corroborated by §9.1.
- NHIS.gov.gh FPHC launch (Apr 2026) + Starr FM/Ecofin.
- Kleinman Center (Mar 2024): Ghana 230 V ±10%; 43 sub-200 V events a month. Corroborates nLine §12.2.
- nLine bucket `2024-03-21.csv` (checked by curl).
- Citi Newsroom (4 Apr 2024): GRIDCo, AFLS relays, no timetable.
- Yen (27 Apr 2026): Akosombo substation fire; widespread outages.
- PUCSL ACEF 2026 deck: Sri Lanka 9 Feb 2025 timeline.
- PUCSL 2016 stability study: UFLS table.
- PUCSL Outlook 2015: 230 V ±6%; 50 Hz ±0.5%.
- FT.lk + National Herald: Sri Lanka 2022, 13-h peak cut.
- SAnews (Oct, Aug 2026) + IOL (Jun 2026): SA streak; load reduction.
- CSIR + Eskom: 2022 load-shedding hours.
- BusinessTech + Polity: NRS 048-9 stage 16.
- eskom-calendar README: licences; archived status.
- esp.info licence agreement.
- Crossref metadata for DOI 10.3390/data11060149.
- IODA API (LK raw signal; GH regions).
- Kaggle API metadata (provenance checks).

**WEAK**
- 3News dumsor tool: 800 MW; 6-h A/B/C (single, unofficial source; framing contradicted).
- Ghana 49.47 / 49.29 Hz events (search snippets only).
- "UFLS keeps f above 49.5" (Ghana press).
- SA 49.5–50.5 Hz band (press quoting MTSAO).
- SA 2023 "332 days" (single compiler).
- *Data* 2026 SA dataset (repository unseen).
- Eskom Data Portal (licence unstated).
- DataFirst survey items.
- Rydin Gorjão & Maritz SA frequency (no data release).

**DO NOT USE (quarantined)**

| Claim / source | Refuted by | Stripped |
|---|---|---|
| "Sri Lanka has free healthcare" with no caveat | WDI OOP 54.8% (2023) | "free" as a filter pass |
| "South Africa has frequent load-shedding now" | SAnews 504 days (4 Oct 2026); IOL; §9.9 | any 2026 SA stage claim |
| EskomSePush API for the demo | ESP licence: free tier is home-residence only, no third-party sharing | — |
| Kaggle `sbonelondhlazi/sa-electricity-historical-data` | Its own description (Eskom + ESP data) vs its CC0 label; ESP licence | CC0 |
| Kaggle `isuranga/load-forecasting-dataset` | No provenance; kW national demand; "corrected" file | — |
| Kaggle `mdeconozzamanecon/load-shedding-problem` | Re-upload class already refuted in §10.1 | Apache-2.0 |
| Nigeria as a "free healthcare" target | WDI OOP 71.9% | — |
| IODA curated events as the only outage label | Empty events vs a clear raw-signal dip for LK 2025-02-09 | — |

---

## Backend system-design pass (2026-10-17)
**Pointer:** the full design, the doability verdicts for PRD v3 and the PRD fix list are in `../system-design-choices.md` (local, not committed). This section holds only the source ledger.
**Method:** PyPI JSON and the Docker Hub tags API were queried directly. Official docs were fetched. The live feeds were curl-probed at ~21:27 BST.
**Community:** the StackExchange API worked and agrees with the nginx docs on SSE buffering. HN Algolia returned only low-signal posts. Reddit was not tried (blocked in earlier passes).

### KEEP
| Source | Supports | Corroboration |
|---|---|---|
| PyPI JSON (2026-10-17): `pydantic-core` 2.50.1 has a cp312 manylinux **s390x** wheel. These are pure Python: fastapi 0.143.3 (now hard-depends on opentelemetry-api), starlette 1.8.0, uvicorn 0.54.0, pydantic 2.14.1, sse-starlette 3.5.0, pg8000 1.31.5, scramp, asn1crypto, pytest 9.1.1, coverage 7.16.2, xmlschema 4.3.2 | The FastAPI + pg8000 + SSE stack installs on s390x | Handoff §9.1; tech ref §3.2; §9.8 |
| PyPI JSON: `cryptography` 50.0.2 and `pycryptodome` 4.0.1 have **no s390x wheels** | AES-GCM can't come from pip | Handoff §9.1; tech ref §3.2 |
| PyPI JSON: `llama-cpp-python` 0.3.36 `[server]` = uvicorn, fastapi, pydantic-settings, sse-starlette, starlette-context, PyYAML | Granite server needs only pure or s390x-wheel extras; install them individually, never reinstall llama_cpp | Image package list |
| Image package list: httpx 0.28.1, anyio 4.15.1, argon2-cffi, PyYAML, tzdata present; no cryptography, pydantic, fastapi or uvicorn | Don't pip httpx; argon2id is available for auth | Handoff §3.2 |
| Docker Hub: `postgres:17`, `debian:trixie`, `nginx:stable`, `python:3.13-slim-trixie` have s390x | Base images OK | Handoff §9.2 |
| nginx/docker-nginx: `stable` is built `FROM debian:trixie-slim` (1.30.6); Debian trixie ships OpenSSL 3.5.7 | Stock nginx can do X25519MLKEM768, so no custom trixie edge build is needed | Tech ref (OpenSSL 3.5.7 in trixie s390x) |
| nginx proxy module docs | `proxy_buffering` defaults on; `X-Accel-Buffering: no`; `proxy_read_timeout` is 60 s between reads | sse-starlette README; SO q/61029079 |
| `openssl-enc(1)` | `enc` does not support GCM/CCM | Official man page |
| `cryptsetup(8)` | A file image gets an automatic loop device (run it on the VM host, not in a container) | Handoff §7.7 |
| OASIS CAP 1.2 spec | Required elements; namespace `urn:oasis:names:tc:emergency:cap:1.2`; polygon ≥ 4 closed pairs; dateTime with no `Z` | PRD §21 |
| pg8000 README (codeberg) | "one thread per connection"; native API, COPY, notifications | Handoff §7.8 |
| Python asyncio.Queue docs | `QueueFull`; not thread-safe; `shutdown()` only in 3.13 | Image is Python 3.12 |
| PostgreSQL 17 CREATE TRIGGER | BEFORE UPDATE OR DELETE row triggers; TRUNCATE statement-level only | Handoff §7.7 |
| OWASP Session Management Cheat Sheet | ≥ 128-bit tokens, HttpOnly/Secure/SameSite, 15–30 min idle, regenerate on login | — (primary) |
| CMS cell-size suppression policy (ResDAC) | Suppress 1–10, allow 0, no back-calculation | Duke guidance; US Census rr2001-01 (complementary suppression); §9.8 emPOWER k=11 |
| scikit-survival `brier_score` (IPCW; Graf et al. 1999) | Censoring-aware Brier; why plain exclusion needs a bound | Graf 1999 (cited, not fetched) |
| Live probes: UKPN (62 records, `limit` ≤ 100, **naive local timestamps**, explicit `Restored`/statusid 5 + `restoreddatetime`); NPg (92, `+00:00`, **no restore timestamp**); SSEN (7, `resolved`, postcode `affectedAreas`, `+0000`); Elexon `from`/`to` OK; postcodes.io bulk OK; IODA v2 OK | Ingest field mapping and grading scope | §12.1 |

### WEAK
| Source | Why |
|---|---|
| OneUptime / objectgraph SSE-through-nginx blogs | Blog-grade; agree with the nginx docs |
| SO q/61029079 (score 13) | Community confirmation only |
| HN "Show HN: tamper-evident audit logs" (2 pts) | Low signal |
| "The lab image's OpenSSL is Ubuntu 3.0 (no ML-DSA)" | Inferred: the image Dockerfile isn't public. Verify in the hour-1 check |
| "pycryptodome AES doesn't use CPACF" | Design knowledge, not re-fetched |

### DO NOT USE (quarantined)
| Claim / source | Refuted by |
|---|---|
| `pip install cryptography` on s390x | PyPI wheel list; handoff §9.1 |
| AES-GCM via `openssl enc` | `openssl-enc(1)` |
| `capparselib` as a CAP dependency (2021, pins lxml 4.6.3, parser only) | PyPI metadata |
| Pinning `postgres:17-bookworm` | Docker Hub: no s390x for that tag |
| `asyncio.Queue.shutdown()` on Python 3.12 | Python docs (3.13+) |
| `pip install httpx` into the lab image | Already present (0.28.1) |


## Home-sensor precursor probe: can a fuse-box/meter sensor predict its own power cut? (2026-10-18)
**Question:** the team's headline is "predict blackouts before they happen" (ADR 2026-10-18). Do household sensor readings carry a usable warning before an outage?

**Method (primary empirical evidence, run on the LinuxONE VM):**
- **Data:** nLine GridWatch Accra, 1–7 Jun 2021. That's 4.76 M readings from 429 plug-in sensors, about one reading every 2 min. **CC BY-NC 4.0.** GPS and respondent/device ids were stripped on the laptop before upload.
- **Label:** this home loses power within 30 min.
- **Features:**
  - the home's own last hour: voltage (pu) level, minimum, volatility, sag share and trend; flicker count; data coverage; grid frequency; hour of day;
  - optional: the share of other district sensors already dark.
- **Validation:** time split, training on 1–5 Jun and testing on 6–7 Jun. XGBoost, compared with three simple rules.
- **Leakage guards:** unit tests prove the label looks only forward and the features never see the future.
- **Code + output:** `backend/app/probe_precursor.py`, `evidence/07_precursor_probe.txt`.

**Result (test base rate 2.1%):**

| Model | ROC AUC | PR AUC | Precision in top 1% of alerts |
|---|---|---|---|
| Own sensor | 0.668 | 0.089 (4.2× base) | 19.7% (9.3× base) |
| + district dark share | 0.684 | 0.092 | 18.8% |
| Rule: flickered in the last hour | 0.568 | 0.071 | — |
| Rule: low voltage | 0.514 | 0.026 | — |
| Rule: district going dark | 0.546 | 0.025 | — |

**Verdicts:**
- **KEEP: home sensors give a modest early warning.** The signal is mostly supply *instability* (recent flicker), time of day and voltage volatility. It beats every simple rule.
- **WEAK: it generalises.** One city, one week, one run, no bootstrap. The Accra grid in June 2021 is not GB or 2026. Corroborating source: Klugman et al., IPSN 2021 (§10.4), where the same fleet showed outages cluster and recur. A second independent dataset was not found tonight.
- **DO NOT USE: "a voltage dip warns of a blackout".** Low voltage alone scores 0.514 ROC AUC, essentially chance, on this data.

**Final call (pitch wording):** "Home sensors flag the homes most likely to lose power in the next 30 minutes: about 1 in 5 of the top alerts come true, roughly 9× chance." Never "predicts blackouts" for this layer on its own. Community input: none sought (empirical primary data).
