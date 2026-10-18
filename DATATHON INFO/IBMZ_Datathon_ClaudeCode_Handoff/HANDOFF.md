# IBM Z Datathon 2026: complete research and build handoff

*Written Sat 17 Oct 2026, about 20:30 BST, for Claude Code. Team: Manchester hub (University of Manchester venue). Our LinuxONE server is called `Datathon4Musketeers`.*

This file holds everything we researched and decided. Where it disagrees with anything in `research/` (written 14–16 Oct), **this file wins**; it carries the facts confirmed on 16 and 17 Oct.

---

## 0. How to use this file (instructions for Claude Code)

1. Read sections 1–4 before writing any code. They hold the hard constraints: the server, the deadline and what judges check.
2. **The idea is not locked yet.** Ask the team which idea they are building before scaffolding anything. The default recommendation is **Spillcast** (section 7, fully specified). Alternatives are summarised in section 8.
3. The "Dialect Decoder" the team mentioned early on was only an *example of the level of novelty wanted*. It is not a candidate idea. Do not propose dialect or language-preservation projects.
4. **Hard rules, never break them:**
   - Everything that matters must run **on the LinuxONE server** (s390x, big-endian). Judges check IP addresses in videos, network traffic and installed packages.
   - Use **open-source models only**: IBM Granite via llama.cpp, TensorFlow, PyTorch, XGBoost, scikit-learn. **No OpenAI, Gemini or Claude API calls** inside the product.
   - All project code is written during the event window (from Sat 17 Oct, about 11:00). Research, data downloads and plans made earlier are allowed.
   - Never commit secrets: the `.pem` key, the Jupyter token or any API key.
   - The VM has **no backups**. Commit and push to GitHub at least every hour.
5. Capture evidence as you build (section 10.4): screenshots and terminal output proving s390x, NNPA timing, encryption and containers. Judges mark it, and it is hard to recreate at 9 am.
6. Work spec-first, in small verified steps (the IBM panel recommends "spec-driven development"). After each step, run the code on the VM and show the output.

---

## 1. Status and deadlines

### 1.1 Key times

| When (BST) | What |
|---|---|
| Sat 17 Oct, 09:00–17:00 | In person at the Nancy Rothwell Building, University of Manchester (kick-off 10:00 in Lecture Theatre A; building from about 11:00) |
| Sat 17:00 onward | Virtual mode. The organisers give a short virtual-mode brief before people leave. Help comes from Discord SMEs |
| **Sun 18 Oct, submission** | Sources disagree: the EMEA guidebook says virtual work ends at 10:00; the Manchester sheet says 11:30; the organiser said on 17 Oct "by tomorrow eleven". **Target 09:30, hard stop 10:00** |
| Sun ~11:30 | Closing ceremony (online links shared by the organisers) |
| 28 Oct | Winners announced |
| 18 Nov | IBM Z Day, where winners can present |

### 1.2 Suggested plan for the remaining hours (from Sat ~20:30)

| Time | Goal | Done when |
|---|---|---|
| 20:30–21:30 | Server access, Docker, Jupyter, the labs (section 3); repo created and cloned on the VM | `docker ps` shows `notebook`; the lab notebooks run; first commit pushed |
| 21:30–23:30 | Data pipeline and baselines (Spillcast: sections 7.3–7.4) | Hourly labels plus rain features built; threshold rule and XGBoost scored on 2025 |
| 23:30–01:30 | LSTM, NNPA timing, FastAPI scoring endpoint | AUC beats the baselines; CPU-vs-NNPA table captured |
| 01:30–03:00 | Map UI, live feed, Granite outlook with RAG, security pieces | End-to-end demo works from a laptop browser |
| 03:00–07:00 | Sleep in shifts; one person polishes the README and evidence | Feature freeze by about 03:00 |
| 07:00–09:15 | Deck, 3-minute video, final screenshots | Video under 3:00; deck PDF stands on its own |
| 09:15–09:30 | Submit on Hack2Skill | Confirmation screenshot |

### 1.3 Status checklist (update as you go)

- [x] LinuxONE server created and ACTIVE (`Datathon4Musketeers`, 148.100.78.95)
- [ ] SSH works from the laptop (the key-permission fix is in section 2.2)
- [ ] Team name: `________`; Hack2Skill team number: `________`. Ask the team; both are needed for the submission title
- [ ] Docker installed; Jupyter container running; port 38888 open; custom token set
- [ ] Four lab notebooks run, with screenshots (the guidebook makes two of them mandatory)
- [ ] Z Xplore "Concepts" badge, which may be required for prizes (section 4.6)
- [ ] Idea confirmed by the team
- [ ] GitHub repo created (public at submission), with every member committing

---

## 2. Our LinuxONE server

### 2.1 Facts (from the portal and IBM's 16 Oct session)

| Item | Value |
|---|---|
| Instance name | `Datathon4Musketeers` (General purpose VM, ACTIVE) |
| Public IP | `148.100.78.95` |
| Login user | `linux1` (the only allowed user; `sudo` works; root login and password logins are disabled) |
| SSH key | Portal key name `DatathonKey1`. Private key on Muhammad's laptop: `C:\Learning Place CS\Hackathons\Manchester IBM Z Datathon\DatathonKey1.pem` |
| Flavour | `AI_LAB`: **3 vCPU, 8 GB RAM (8192 MB), 50 GB disk** |
| Image | `Ubuntu24.04-Datathon` |
| Created | 2026-10-16 13:28:25 (portal time) |
| Lifetime | 30 days (IBM, 16 Oct). Older docs say 120 days for normal trials |
| Hardware | IBM **z17** (machine type 9175, LinuxONE 5) at Marist University, under the z/VM hypervisor. **Telum II AI accelerator (NNPA) enabled** for the VM, as shown by `lscpu` |
| Architecture | **s390x, big-endian** |
| Backups | **None.** Keep everything in git |
| Rules | One server per team. If it stops responding to SSH: Stop, then Start, in the portal (https://linuxone.cloud.marist.edu/#/login → Manage Instances). A server in "shutdown" just needs Start |
| Support | linux1@us.ibm.com; Discord SME channel (70–80 IBM SMEs) |

### 2.2 Windows SSH (Muhammad's laptop, PowerShell)

The key file lives in a path with spaces. Windows OpenSSH also refuses keys other accounts can read (error: `Bad permissions… UNPROTECTED PRIVATE KEY FILE`). Fix it once:

```powershell
$k = "C:\Learning Place CS\Hackathons\Manchester IBM Z Datathon\DatathonKey1.pem"
icacls $k /inheritance:r
icacls $k /remove:g "BUILTIN\Users" "Authenticated Users" "Everyone"
icacls $k /grant:r "${env:USERNAME}:(R)"
ssh -i $k linux1@148.100.78.95
```

**Pitfalls already hit:**
- IBM's guide prints `ssh –i` with an en dash (–). Type a normal hyphen (`-i`).
- Quote paths with spaces.

**Recommended `~/.ssh/config` alias** (lets Claude Code run `ssh datathon "<cmd>"`). Copy the key to `$HOME\.ssh\DatathonKey1.pem` first and re-run the `icacls` lines on the copy.

```
Host datathon
    HostName 148.100.78.95
    User linux1
    IdentityFile ~/.ssh/DatathonKey1.pem
    ServerAliveInterval 30
```

**More SSH tips:**
- `REMOTE HOST IDENTIFICATION HAS CHANGED` means IPs get reused: `ssh-keygen -R 148.100.78.95`.
- Copy files to the server: `scp -i <key> ./file.csv linux1@148.100.78.95:~/shared/`. Files in `~/shared` appear in Jupyter.
- **Teammates:** don't pass the private key around. Each member runs `ssh-keygen -t ed25519` and sends their `.pub`. On the server: `echo "<their public key>" >> ~/.ssh/authorized_keys`. This is also a security talking point.
- If the venue Wi-Fi blocks port 22, use a phone hotspot.

### 2.3 How Claude Code should drive the server

- **Run Claude Code on the laptop**, not on the VM. Do not assume Claude Code or VS Code Remote-SSH work on s390x.
- Drive the VM over SSH: `ssh datathon "cd ~/project && <command>"`.
- Sync code through git: commit locally, push to GitHub, then `git pull` on the VM. GitHub is required for submission anyway, and judges read the commit history. `scp` works for quick files.
- Run long jobs on the VM with `nohup … &`, `tmux`, or as docker compose services, so they survive SSH drops.
- Data files over 100 MB stay out of git. Keep them in `~/data` on the VM; document how to fetch them in the README.

### 2.4 Networking

- **Only port 22 is open by default** (iptables). Open a port with `sudo iptables -I INPUT -p tcp --dport <port> -j ACCEPT`. Persist the rules on Ubuntu with `sudo bash -c "iptables-save > /etc/iptables/rules.v4"` (IBM's lab README shows the RHEL path; this is the Ubuntu one).
- **Docker caveat:** ports published with `-p` are DNAT-forwarded and **bypass the INPUT chain**, so they can be public even without an iptables rule. Bind internal services to localhost (`-p 127.0.0.1:5432:5432`) and expose only the app or reverse proxy.
- The Jupyter container runs with `--network host`. Anything you serve from inside it (for example uvicorn on 8000) is on the host network and needs an iptables rule to be reachable.
- Outbound internet works: get.docker.com, PyPI, the Marist registry, Hugging Face, GitHub and open-data APIs.
- High ports such as 38888 and 8000 are reachable. Whether 80/443 are reachable is not documented: test with `python3 -m http.server 8080` and a browser. Fallback: an SSH tunnel, `ssh -L 8000:localhost:8000 datathon`.

### 2.5 Day-1 probe (run it, save the output, screenshot it for the proof slide)

```bash
cat /etc/os-release | head -2; uname -m; nproc; free -h; df -h /
lscpu | grep -E "Architecture|Byte Order|Machine type|Model name|Hypervisor"
lscpu | grep -i nnpa            # Telum AI accelerator line: screenshot this
for f in msa vxe vxe2 nnpa; do grep -qw $f /proc/cpuinfo && echo "$f: yes" || echo "$f: no"; done
openssl version; openssl speed -seconds 2 -evp aes-256-gcm 2>/dev/null | tail -2   # CPACF crypto
sudo iptables -L INPUT -n
cat /sys/firmware/uv/prot_virt_guest 2>/dev/null || echo "no Secure Execution (expected on z/VM)"
```

Expected results:
- `uname -m` → `s390x`, and `Byte Order: Big Endian`.
- Machine type `9175` = z17.
- `nnpa` present.
- 3 vCPUs.

---

## 3. Jupyter Lab ML container (IBM's lab image)

Source: https://github.com/linuxone-community-cloud/jupyter-lab-ml (README updated 16 Oct 2026; copy in `reference/`).

### 3.1 Setup on our Ubuntu server (run once)

**Block 1: install Docker.** Paste this, then **log out (`exit`) and SSH back in** so the docker group applies:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

IBM's README instead runs `sudo usermod -aG docker $USER; newgrp docker`, then `sudo systemctl start docker`, then `exec bash`. Either works; just don't paste anything after an `exit`.

**Block 2: start Jupyter.** Run this after logging back in. Set your own token from the start (see the security note below):

```bash
sudo systemctl start docker
mkdir -p ~/shared && chmod a+w ~/shared
TOKEN=$(openssl rand -hex 24); echo "Jupyter token: $TOKEN"     # save it somewhere private
docker run --network host --name notebook -v /home/linux1/shared:/home/ibm-user/shared \
  -d registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest \
  jupyter notebook --ip=0.0.0.0 --NotebookApp.port=38888 --ServerApp.port=38888 \
  --ServerApp.token="$TOKEN" --ServerApp.allow_origin='*'
#   README: "You may need to add --security-opt seccomp=unconfined"
#   The image is several GB; the first pull takes minutes
docker ps                 # expect a container named "notebook"
sudo iptables -I INPUT -p tcp --dport 38888 -j ACCEPT
```

Open **http://148.100.78.95:38888** and enter your token.

**If the token-arguments run fails** (`docker logs notebook`): start the container without the `jupyter notebook …` arguments. The default token is then **`Your_Token1`**.

**Security note:**
- That default token is published in IBM's README, so anyone can log in to a public IP with it. Use your own (good security evidence for the judges).
- Alternative: close 38888 and use `ssh -L 38888:localhost:38888 datathon`.
- **Set the token before running the labs.** `docker rm -f notebook` throws away everything not saved in `~/shared`; the lab notebooks and data live inside the image. Copy anything you want to keep into `shared/` first.

**Troubleshooting (IBM FAQ):**
- Docker permission denied → `exec bash` or reconnect SSH.
- Shared-folder write errors → `sudo chown -R 1000:1000 /home/linux1/shared`, or `sudo chown linux1:linux1 ~/shared && sudo chmod a+w ~/shared`.
- Redeploy → `docker logs notebook; docker rm -f notebook; docker run …`.
- Disk full → `docker images -a; docker rmi …` or `docker system prune`.
- Memory → `docker stats; free -h`; restart the kernel and clear outputs.
- Install a missing package from a notebook → `import sys; !{sys.executable} -m pip install <pkg>`.
- Jupyter UI uploads are limited to **200 MB per file**; use `scp` into `~/shared` for bigger files.

### 3.2 What is inside the image (from `packages.txt`, 188 pins)

- **Python and venv:** Python 3.12 in `/opt/venv`.
- **Deep learning:**
  - `tensorflow 2.18.1` and `keras 3.14.0`, with **`ibm-zdnn-plugin 2.3.0`** (TF → NNPA)
  - `torch 2.11.0+cpu` with **`torch_nnpa 1.5.0`** (a PyTorch `'nnpa'` device)
- **Classic ML:** `xgboost 3.4.1`, `scikit-learn 1.9.0`, `numpy 2.0.2`, `pandas 3.0.6`, `scipy 1.13.1`, `sklearn-pandas`, `scikit-image`. **No** lightgbm, statsmodels or imbalanced-learn.
- **GenAI:**
  - **`llama_cpp_python 0.3.36`**, built with zDNN and OpenBLAS
  - `transformers 5.19.0`, `tokenizers`, `safetensors`, `huggingface_hub`
  - **`rank-bm25`** (the labs' RAG retrieval) and `pypdf`
- **Model exchange:** `onnx 1.22.0`, `tf2onnx`, `skl2onnx`, `sklearn2pmml`, `pypmml`. **No onnxruntime.**
- **Web:** `requests`, `httpx`, `matplotlib`, `seaborn`. **No FastAPI, uvicorn, Flask or sentence-transformers**: `pip install` them on top (they install cleanly).
- **The loan demo:** its `loan_demo` package (`rag_utils`, `model_utils`, `pdf_utils`), its `sample_data/` and the Granite model file (`granite-3.3-2b-instruct-be.Q4_K_M` GGUF, big-endian) ship **inside the image**, not on GitHub. Find them with:

  ```bash
  docker exec notebook find / \( -name rag_utils.py -o -name '*be.Q4_K_M.gguf' \) 2>/dev/null
  ```

  Copy them out with `docker cp notebook:<path> .`

### 3.3 The four reference notebooks (copies in `reference/lab_notebooks/`)

| Notebook | What it teaches | Pattern to reuse |
|---|---|---|
| `Fraud_LSTM_Keras_TF.ipynb` | 2-layer LSTM over sequences of 7 card transactions (IBM TabFormer-style data, 24M rows on Kaggle). Exports to ONNX (opset 13). Ends with a "NNPA" benchmark cell | **The template for Spillcast's sequence model** |
| `Loan_Approval_Demo.ipynb` | **Predictive + generative hybrid:** XGBoost risk score; Granite extracts features from PDFs; BM25 RAG over policy PDFs; Granite writes a recommendation and answers questions. All on the VM | The template for our "explain" layer |
| `Churn_Scikit_PyTorch.ipynb` | Random Forest → PMML; PyTorch logistic regression; EDA. Sets `TORCHDYNAMO_DISABLE=1` to avoid an onnxruntime dependency | Baseline and EDA patterns |
| `Digit_Class_TensorFlow.ipynb` | Dense MNIST classifier → ONNX and SavedModel; a batch-1000 throughput benchmark. IBM's figure is a median of about 3.6 ms per **batch of 1,000 images** (about 275k images/s), measured in eager mode; "per image" in the talk was a slip | Benchmark cell |

The guidebook names two labs as mandatory prerequisites: "Predictive AI, hybrid multi-model" and "Predictive AI + Generative AI". Run **all four** and screenshot each finished run.

### 3.4 Using the Telum AI accelerator (NNPA): do it properly and measure it

IBM said on 16 Oct that technical design is "the primary" criterion and should leverage "security or Telum acceleration, or both". So **every pick must run a neural model on NNPA and show CPU-vs-NNPA timing.**

- **TensorFlow (lab image, `ibm-zdnn-plugin`).** zDNN is used in **graph mode only**: call `model.predict(x)` or a `@tf.function`. The lab notebooks benchmark in eager mode (`model(x)`), and their check only tests that `_z_ops.so` exists.
  - Turn NNPA off for the A/B run with `NNPA_DEVICES=0`, set in the environment **before** importing TensorFlow (use a separate process).
  - `ZDNN_ENABLE_PRECHECK=true` logs each op zDNN handles.
  - zDNN accelerates LSTM cells, MatMul/Dense, Sigmoid, Relu, Softmax and BatchMatMul.
- **PyTorch (`torch_nnpa`).** Inference only (training on NNPA is not supported):

  ```python
  import torch, torch_nnpa
  model.to('nnpa')
  with torch.inference_mode():
      out = model(x.to('nnpa'))
  ```

  Debug with `TORCH_NNPA_DEBUG=1`. If NNPA is absent, the device is not registered.
- **llama.cpp (Granite).**
  - The zDNN backend works on **z17 only**, and only for **F32/F16/BF16/Q8_0** weights.
  - The lab's Granite file is **Q4_K_M**, which runs on CPU SIMD + OpenBLAS, not NNPA.
  - To exercise NNPA, try `Granite-3.3-2B-Instruct-BE` **Q8_0** (2.69 GB) and benchmark it against Q4_K_M. Expect a few tokens per second either way on 3 vCPU.
  - **Only the lab image's `llama_cpp_python` is built with zDNN** (`-DGGML_ZDNN=ON`; the Loan notebook checks for `libggml-zdnn*.so`). The ghcr images (`ghcr.io/ggml-org/llama.cpp:server`, `:full`) are built **without zDNN**: CPU and OpenBLAS only, for every quant.
  - So run the Q8_0 vs Q4_K_M comparison with `llama_cpp_python` inside the lab image, and label any ghcr benchmark "CPU". If the deck claims Granite uses NNPA, serve it through `llama_cpp_python`.
- **Other options (need extra setup):**
  - **Snap ML** (`pip install snapml`, NNPA tree inference; needs zDNN 1.1.x)
  - **IBM zDLC** (`icr.io/ibmz/zdlc:5.1.0`: ONNX → `.so` with `--maccel=NNPA`; `-march=z16` code also runs on z17)
  - IBM's Triton container
  - The `icr.io` images need a free IBM Cloud API key: `docker login -u iamapikey icr.io`
- **Benchmark template** (run once with NNPA, once with `NNPA_DEVICES=0`, each in a fresh process):

  ```python
  import os, time, numpy as np, tensorflow as tf
  model = tf.keras.models.load_model("spill_lstm.keras")
  x = np.load("bench_batch.npy").astype("float32")      # e.g. every overflow, one batch
  model.predict(x, batch_size=len(x), verbose=0)          # warm-up (graph build)
  ts = []
  for _ in range(20):
      t0 = time.perf_counter(); model.predict(x, batch_size=len(x), verbose=0); ts.append(time.perf_counter() - t0)
  ts.sort(); print(f"NNPA_DEVICES={os.environ.get('NNPA_DEVICES','(default)')}  batch={len(x)}  median={ts[10]*1000:.1f} ms  p95={ts[18]*1000:.1f} ms")
  ```

  Put both numbers in a table on the proof slide. **Never claim a speed-up you didn't measure.**

---

## 4. Event rules, themes and what the judges look for

### 4.1 Official rules (participant guidebook)

| Item | What it says |
|---|---|
| Themes (all under "AI for Good") | **1. Real-time AI for critical decisions** ("Detect. Decide. Respond."). **2. AI Secured: innovation without exposure** ("Powerful AI. Protected Data."). **3. Wildcard: beyond the obvious** |
| Platform | Must use IBM Z / LinuxONE Community Cloud (Marist), event code SSF2026, and the Jupyter Lab ML image |
| Prerequisites | Complete two labs before building: "Predictive AI, hybrid multi-model" and "Predictive AI + Generative AI" |
| Evidence | Screenshots of containerisation, security, scalability and compute |
| Submission (Hack2Skill) | A video of **3 minutes or less** covering the problem, the data, the solution and how it uses IBM Z, **showing the LinuxONE instance and the model**. Plus a GitHub/GitLab link (or zip), a deck, and a list of every open-source resource. Title format: `[Team Name_IBM Z Datathon 2026 Project]` (the hosting guide also mentions the team number). Flowchart and prototype optional |
| Rules | Built within the event window; original work; open source allowed with credit; nothing hateful or political |
| Prizes | $50k+ pool. **Top 3 per hub**, so Manchester competes within Manchester. Special awards: Most Innovative AI Theme, Most Creative AI Solution, Highest Participation, Best IBM Z Advocacy. A separate AI Innovation Excellence award rewards novelty and technical depth |
| Rubric | **4 criteria × 10 points** (half-points used): value/theme fit, novelty, technical design (LinuxONE + open-source AI/ML), execution/pitch |

**What a "9–10, exceptional" mark means for each criterion:**
- **Value:** an "impactful solution to a critical need … seamless theme integration".
- **Novelty:** "highly innovative … a breakthrough in concept … strong end-to-end solution components".
- **Technical:** "optimizes LinuxONE … features with exceptional exploitation of AI/ML … fully exploits security and/or compute".
- **Pitch:** "a highly professional and well-orchestrated team presentation … and a compelling solution demo", within the time limit.

An older IBM *hosting guide* has a 100-point rubric. It awards bonuses for a community-impact story for under-served groups (+5), live-demo excellence (+3) and a well-documented public repo (+2). Its weights are problem relevance 20, data and method 20, innovation 20, IBM Z integration 15, presentation 10, reproducibility 5. Follow the participant guidebook; the bonuses point the same way.

### 4.2 IBM technical enablement session, 16 Oct (Alex and Bruce, IBM). Transcript in `transcripts/`

**Technical design is weighted most:**
> "the key one I would say is a technical design… showcase that your project runs on the LinuxONE. It leverages either security or Telum acceleration, right, or both. And this first one is actually the highly weighted criteria… the primary one."

**The other criteria:**
- **Novelty:** "make sure your submission is original".
- **Pitch:** follow all the requirements, "showcase that it is running on LinuxONE environment".
- **Community value:** "identify specific problem and who… is going to benefit".

**The server:**
- 30 days; one server per team; 3 vCPU, 8 GB, 50 GB.
- Images "Ubuntu 24.04-datathon" or "Red Hat 9.8-datathon".
- The "AI lab" flavour only appears with event code SSF2026.
- A z17 (machine type 9175) with NNPA enabled; `lscpu | grep nnpa` shows it.
- Labs: four notebooks (section 3.3). The loan-approval hybrid is new this year: "the most exciting lab".
- "Take screenshots of evidence that you run it on LinuxONE."

**Theme examples IBM gave:**
- **Theme 1:** real-time payment fraud detection, or anything with real-time data and immediate action.
- **Theme 2:** AI with security technologies, private and privacy-aware.
- **Theme 3:** bold ideas, for example food-waste prediction or a personal student-success coach.

### 4.3 Manchester kick-off keynote, 17 Oct (Ben Davis, Lewis James, Joe Winchester; IBM)

**Theme 1, Real-time AI for critical decisions.**
- Mission-critical workloads: banking, healthcare, insurance.
- Examples: real-time fraud detection, and risk scoring *inside* a transaction ("fast, but… the work going through them is legitimate").
- "Agentic solutions within our transaction".

**Theme 2, AI Secured.**
- Quantum-safe encryption: Shor's algorithm (Peter Shor, 1990s) could break today's encryption, so there is "this big rush to… implement quantum-safe encryption algorithms".
- AI-powered fraud detection that blocks a fraudulent transaction *before* it goes through.

**Theme 3 / "think big, think beyond the obvious" (Joe, a judge).**
- "Most of the innovations have really come from a small spark… very personal."
- Example: a team built a device on a visually impaired relative's white stick, using compass and AI recognition of cars and buildings. "They didn't finish, but… we awarded them very, very highly."
- Valued areas: healthcare, saving water, sustainability, "ethical computing… making the world a better place".
- "You're not constrained by those two guardrails."
- "We're not expecting within 24 hours… the same sort of solutions. We just want you to show… prowess and enthusiasm."

**Enterprise pillars the judges think in:**
- Security (end-to-end encryption).
- Resilience and uptime.
- Fail-safe and rollback ("if you sent me ten pounds and something happens in between…").
- Regulation and **audit trails** (healthcare, banks, government, military).

**LinuxONE:** Linux running natively on Z hardware (Telum processor, Spyre AI accelerator cards), containers and open source with no porting.

**Stats quoted (quote only with a linkable source; keynote numbers are not always consistent):**
- 1.1 million IBM Z transactions a second.
- 19% of the world's IT workloads and 72% of transactional workloads run on mainframes.
- One organisation processes 2 quadrillion dollars a year.
- Skills gap: 71% of IT leaders say their mainframe team is understaffed; 93% find mainframe skills hard to hire; 91% are expanding their mainframe footprint.

### 4.4 Panel Q&A with the judges, 17 Oct (Joe, Ben, Lewis)

**"What makes a winning project?" (Joe, who organises judging):**
- "If we can tell that you have something amazing… but you haven't used the LinuxONE environment that was provided for you, that means you won't win. You have a box and you score: have you used that? So we need the evidence."
- "Sometimes… we might go back to them and go, it was amazing, but… we couldn't see it. Can you prove it? … **We look at the network traffic. We look at IP addresses on the videos.**"
- "We look for collaborations of the team… if you just have one person that's a superstar… and the other ones didn't, that is… going to be a bad mark. We want to see that everybody on the team did something": coding, documentation, tests, or the manager role putting presentations together.
- He also warned about cheating; the recording cuts off there.

**AI coding is fine.**
- "Can I use AI to write code? Course you can."
- Engineers are now architects. Use spec-driven development and multi-shot prompting rather than one giant prompt.

**Background they mentioned:**
- IBM Z Xplore badges (Concepts → intermediate → "All Star"); COBOL, PL/I, JCL.
- Java and Python on the mainframe; customers using AI to turn COBOL into Java.
- Resilience and empathy matter, not just IQ.

### 4.5 Logistics briefing, 17 Oct (organisers)

**What to submit:**
- Upload **screenshots** with the submission.
- **List every open-source library** you used; the submission form has a question for each required item.
- **A 3-minute (or shorter) pitch video** is "the critical part". "Focus on the pitch a lot… spend between the 24 hours some time on creating the pitch."
- The deck matters: it summarises the work. A flowchart is optional.

**Pitch beats size:**
- A Bangalore team won with a simple project: which lakes are being polluted, by whom, at what time.
- They won because of how they framed a critical local problem.

**Help channels:**
- Discord has an IBM Z SME help channel with 70–80 SMEs, for login, instance and setup problems.
- There is also a Manchester UK Hub channel.
- The guidebook has the login link and all instructions; the submission link is at the top.

**Timing:**
- Hybrid: in person until 17:00, then virtual. Return to the main room for the virtual-mode brief before leaving.
- Closing ceremony next day around 11:00–11:30.
- "By tomorrow eleven, if you can submit."

### 4.6 Pre-event prep sessions: key points (detailed notes in `research/08*`, transcripts in `transcripts/prep_session_*`)

**How to win (Joe, IBM judge for 4–5 years).**
- **How marking works:**
  - Marks are out of 10 in half-points. "If you're saving lives you score a 10 in that column."
  - Unfinished is fine if the next steps are clear.
  - Explain your choices, your rejected options and your failures.
- **What the problem should be:** personal and local.
- **The team:**
  - Teamwork is marked; nobody should dominate the video.
  - He quoted *The Tipping Point*: a team of only "inventors" usually fails; you also need a salesperson and a connector.
- **The code:**
  - A public repo with real commits.
  - Vibe coding is fine.
  - "We look at IP addresses, we look at packages" to confirm IBM Z use.
- **His request:** scam protection for vulnerable adults. His 85-year-old father got a "Hey Dad… new phone" message; he wants a tool that spots someone who "says they know your son, but clearly doesn't know your son's name".

**IBM Z & LinuxONE keynote, with the 2025 winners.**
- The **Z Xplore Concepts badge** (4–8 hours) is "needed to qualify for the prizes". **Verify this on Discord**; the guidebook only "strongly encourages" it.
- AI must be "fit for purpose". Z's strength is classic ML scoring every transaction in milliseconds.
- Avoid blockchain, closed LLMs and GPUs.
- Winners' advice: start from the problem, don't make it bigger, research it, show a working demo with a number.

**AI on IBM Z (Steve Warren, IBM STSM).**
- "Bring AI to the data." Use predictive AI where milliseconds matter.
- Train anywhere, export to ONNX or PMML, run on Z.
- Build trust: a "simulating" mode, a success-rate display, saying when AI is not the answer, and guardrails on inputs, outputs and tools.

**Trust & identity (IBM Z Security product manager).**
- "The most interesting problems usually put AI on both sides" (attacker and defender).
- Aim for the "tomorrow" column: predict, prevent, enforce automatically.
- "Machines need identities too."
- Use the NIST five functions. Assume breach; zero trust for insiders; "ask them to prove it".
- First question for any Theme 2 pitch: "What trust am I protecting, and from whom?"

**Orientation (Shooting Stars Foundation).** It's a theme, not a problem statement: "look around your surroundings". A Bangalore team mapped lakes that needed cleaning.

### 4.7 Where sources conflict, and what to do

| Topic | Conflict | Do this |
|---|---|---|
| Submission deadline | 10:00 (EMEA guidebook) vs 11:30 (Manchester sheet) vs "by eleven" (organiser, 17 Oct) | Submit by 09:30–10:00 Sunday |
| Prize eligibility | Keynote: badge needed. Guidebook: badge encouraged | Earn the Concepts badge; ask in #helpdesk |
| Old code | Joe: porting earlier code is fine. Guidebook: built during the event | Build fresh |
| Submission format | Joe: any format. Guidebook: video + repo + deck | Follow the guidebook |
| Jupyter port | 38888 (2026 README) vs 3888 (2025 captions) | 38888 |
| VM size and trial length | Old docs: 2 vCPU/4 GB, 120 days | **Settled 16 Oct:** 3 vCPU / 8 GB / 50 GB, 30 days |

---

## 5. What the 481 projects from 2025 tell us

We read every 2025 deck and the project spreadsheet. Text from all 481 decks, with OCR for 54 that were image-only, is in `data/2025_deck_texts.zip`. One-line classifications are in `data/IBM_Z_Datathon_2025_classified.csv`.

### 5.1 Where projects and prizes went

**Two of the three busiest areas won nothing: education (50 projects) and agriculture (42).** 8 of the 12 prizes went to safety, health, governance and fraud. Eleven of the twelve winners were real-time decisions about safety, health, money or government.

| Area | Projects | Prizes |
|---|---|---|
| Education, careers, jobs | 50 | 0 |
| Agriculture, food | 42 | 0 |
| Health: care and hospital ops | 40 | 1 |
| Environment: pollution, water, waste | 40 | 1 |
| Health: diagnosis, imaging | 30 | 2 |
| Climate, energy | 30 | 0 |
| Governance, legal, civic | 29 | 2 |
| Mental health | 24 | 0 |
| Transport | 24 | 0 |
| Finance: inclusion, credit, trading | 21 | 1 |
| Cybersecurity, identity | 21 | 0 |
| Other | 20 | 0 |
| Finance: fraud, scams | 19 | 1 |
| Disaster, weather | 19 | 1 |
| Accessibility, elderly care | 17 | 0 |
| Public safety, crime | 16 | 2 |
| Misinformation, deepfakes | 16 | 0 |
| Supply chain, business | 13 | 0 |
| Social welfare, poverty | 10 | 1 |

Bangalore 1st is counted under finance. The winners list names "GAT097 RUNTIME TERRORS": the name matches deck GAT149, the code matches Dedcell (GAT097). GAT149 is more likely.

**2025 prize decks:**
- **Global 1st:** Life Aspirant's (plastic in water). A plain deck; it won on problem plus working demo.
- **Global 2nd:** Hackasaurs (food demand for public kitchens). The richest evidence: model comparison, setbacks, a live L1CC IP.
- **Global 3rd:** Gradient Ascent (retinal screening triage).
- **London 1st:** Medikate (IBMLOND015, medication non-adherence).
- **London 2nd:** CrisisLens (AlphaPeterGamma, riot hotspots with a GNN).
- **Germany 1st:** IBMGER004 (interstate conflict early warning).
- **Chennai 1st:** Tech Titans (trading fraud; polished, but its claims were thin).
- **Chennai 2nd:** BIG IRON (heart MRI; real Db2/watsonx screenshots).
- **Bangalore 2nd:** YuktiX (fog accidents).
- **South Africa 1st:** URSI (TUT027, route safety).
- **South Africa 2nd:** TUT041 (public-finance anomalies).

Full profiles are in `research/02*` and `research/03*`.

### 5.2 Proof of LinuxONE was rare, even among winners

| Shown in the deck | All 481 | 12 prize decks |
|---|---|---|
| Mentions LinuxONE or IBM Z at all | 236 | 8 |
| An s390x terminal (`uname`) | 1 | 0 |
| A Community Cloud server IP (148.100.x.x) | 5 | 1 |
| Names the Telum chip | 3 | 2 |
| Names an open LLM (Granite, Llama, Mistral) | 9 | 0 |
| Calls a closed LLM API (OpenAI, Gemini) | 27 | 0 |
| Reports metrics (accuracy, F1, AUC) | 207 | 6 |

Generative AI appeared in 63 projects (13%). **No deck timed anything on the chip.** A proof slide is cheap and rare.

### 5.3 Lessons from the UK and Germany hubs (closest to our judges)

- **London 1st, Medikate:**
  - It opened with a sourced UK number: a 2018 study's estimate of up to about 22,000 deaths a year in England linked to medication errors.
  - It had one clear user (the GP), a risk score with a full classification report, and a working FastAPI + React app.
- **London 2nd, CrisisLens:**
  - A graph neural network on a real tweet dataset.
  - It set its predictions **beside a real record** of where police requested camera footage.
  - It included a **video of their LinuxONE instance**.
  - Checking against a real event is the move to copy.
- **Germany 1st:** conflict early warning from public trade and conflict data. Their deck was a one-page abstract.
- **The five London entries that won nothing:**
  - a travel planner (GPT-4.1)
  - an upskilling site
  - a legal chatbot on the OpenAI API
  - bike theft in Toronto
  - Parkinson's risk built on US statistics
  - What they shared: convenience, closed models or problems far from home.
- **IBMGER003** wrote that they lost six hours connecting their APIs to LinuxONE. Set the server up in hour one.

### 5.4 What winners share (2021–2025)

- A named place, a named group and one big number.
- Several public data sources joined together.
- 3–5 models compared properly, with F1/AUC, class imbalance handled, and explainability.
- An output someone acts on: a map, risk tiers, alerts.
- A visible LinuxONE story: Docker on the VM, measured latency, s390x issues solved and explained.
- Past winners' write-ups mention big-endian model bugs they had to fix. See `research/07*`.

---

## 6. The ideas: portfolio, ranking and decision

### 6.1 Ranking (our estimates against the four criteria, re-scored 16 Oct after IBM's session)

| # | Idea | Theme | Value | Novelty | Tech | Pitch | Total /40 | One line | Biggest risk |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Spillcast** | 1 | 9.5 | 8.5 | 9.5 | 9 | **36.5** | Forecasts sewage spills into Greater Manchester rivers six hours ahead, and flags spills the rain can't explain | Coarse rain data misses cloudbursts; water companies already buy AI for their own networks |
| 2 | **Cable Watch** (rename: "Snag") | 1 (+2) | 7.5 | 8 | 9.5 | 8 | 33 | Live ship tracking flags anchors dragged, or identities faked, near subsea cables | Real-world rivals; anchor drags must be simulated |
| 3 | **Memory Lane** | 1 | 9.5 | 7.5 | 7 | 8.5 | 32.5 | A family's knowledge becomes a ranked search map for a missing person with dementia | IBMGER002 (2025) did dementia wandering; weak chip fit |
| 4 | **Proof of Kin** | 2 (+1) | 9 | 7 | 9 | 7.5 | 32.5 | Verifies a "Hi Mum, new number" sender by writing style and shared memories; the bank pauses on a signed token | About 15 scam projects in 2025; hard to demo convincingly |
| 5 | **Lights Out, Lives On** | 1 | 9 | 8.5 | 7 | 8 | 32.5 | Joins live power cuts to where electricity-dependent people live, to rank welfare checks | Labels: now solvable with ENWL outage history (section 8.4) |
| 6 | **Ember** | 3 (+2) | 8.5 | 9.5 | 6.5 | 7.5 | 32 | Targets fire-safety visits where emollient-cream and smoking fire deaths cluster | Monthly area-level data |
| 7 | **Mule Ring Radar** | 2 | 7.5 | 7.5 | 9.5 | 7 | 31.5 | Banks find money-mule rings together without sharing customer data (private set intersection) | Abstract demo; Eclipsera (2025) did cross-bank federated learning |
| 8 | **Martha's Voice** | 1 | 9 | 7.5 | 7.5 | 7.5 | 31.5 | Fuses a family's "he's not right" with vital-sign trends under Martha's Rule | Concern text is synthetic |
| 9 | **Shell Alarm** | 2 (+1) | 7 | 8 | 7.5 | 7.5 | 30 | Watches the Companies House stream for companies registered at strangers' homes | New ID checks may blunt it |

**Decision rule:**
- Free to choose → **Spillcast**: real labels, a live feed, local rivers, and an LSTM on the chip like IBM's fraud lab.
- Want the boldest tech demo and accept simulated incidents → **Cable Watch**.
- Committed to the submitted abstract (the team was advised to submit **Memory Lane**) → build that, upgraded as in section 8.2. Ask on Discord whether the final project may differ from the abstract.

The kick-off keynote explicitly praised projects on "saving water" and "sustainability", which supports Spillcast. Joe also asked for scam protection for vulnerable adults, which supports Proof of Kin.

### 6.2 Novelty check against all 481 projects from 2025 (details in `research/01_overlap_with_2025_projects.md`)

| Idea | 2025 status | Nearest 2025 project | How to stay clearly new |
|---|---|---|---|
| Spillcast | **Untouched.** Four decks mention sewage; none forecasts spills. About 8 flood-prediction projects exist | Flood alerts (e.g. Bengaluru) | Frame it as sewage spills, not floods. Public-facing forecasts plus an unexplained-spill audit |
| Cable Watch | **Untouched** (no AIS or ship data at all) | Missile tracking (SAV088); oil-spill radar | Behaviour model, not geofences; replay the Eagle S incident |
| Memory Lane | **Partly done** | IBMGER002: ML on a worn GPS tracker to detect when someone gets lost | "They detect getting lost; we find someone already missing, with no tracker." Life-story priors, Bayesian search, break-glass vault |
| Proof of Kin | **Partly done** (scams crowded) | Dedcell (passwordless login, behavioural biometrics); TradeSentinel (signed trust seal, Chennai 1st); ZeroTrustX | "We verify the sender, not the content." Per-contact style model; shared-memory challenge; a signed token to the bank with no chat content |
| Lights Out | Untouched for the join | Hackaroake: outage forecast with no people data | Household-level vulnerability ranking, re-ranked live |
| Ember | Untouched | Only wildfire projects | Prescribing data for a non-clinical risk |
| Mule Ring | Partly | AegisZ (rings at one bank); Eclipsera (cross-bank FL for credit) | Cross-bank edges via PSI/MPC, which nobody built |
| Shell Alarm | Untouched | Procurement anomaly projects | First to use company-register data |
| Martha's Voice | Partly | OncoPredict Lite (post-discharge carer reports + vitals) | In-hospital NEWS2 trends + free-text family concern + the Martha's Rule pathway |

**Privacy tech in 2025:**
- One real differential-privacy toolkit (Team Epsilon), one or two simulated federated-learning set-ups, and one PII-redaction tool.
- **No homomorphic encryption, PSI or MPC; no verifiable enclave.**
- About 17 decks claimed "secure enclaves", which are impossible on these z/VM guests.

### 6.3 Real-world rivals (checked 16 Oct)

- **Spillcast:**
  - *Public tools show spills that are already happening:* Rivers Trust map, Surfers Against Sewage, floodradar (live status plus a rainfall chart, no spill forecasts) and Top of the Poops.
  - *The EA's pollution risk forecasts* covered 171 of 424 bathing waters in 2023 and "do not specifically make predictions of sewage pollution".
  - *Operator-side AI exists:* StormHarvester ("machine learning and hyperlocal rainfall prediction", working with 75% of UK wastewater utilities). It serves the water companies, not the public.
- **Cable Watch:**
  - *Commercial AIS cable protection:* NKT (rule-based protection zones, 2021) and Vesper Marine Guardian (2018).
  - *Military:* the UK-led JEF's Nordic Warden (AI on AIS, Jan 2025).
  - *A free prototype called "Submarine Cable Watch"* from Space Data (Japan, 21 Jul 2026, synthetic tracks), so **rename ours**.
- **Proof of Kin:** current advice is manual only (call back on the known number; Starling's "safe phrase" campaign). No sender-verification tool was found.
- **Memory Lane:** police use the paper Herbert Protocol form and search tools such as SARCALL and IGT4SAR. No AI tool personalised from a life story was found.

### 6.4 Seed bank (smaller ideas, evidence-backed; details in `research/06*`)

- **Throwline Gap:** drowning risk where rescue throwlines are missing (PFD: Alex Crook).
- **Battery Watch:** e-bike battery fires (PFD: Mohsin Janjua).
- **Mould Radar:** damp and mould risk ahead of Awaab's Law.
- **Wrong-Way Watch:** sat-nav wrong-way slip roads (PFD: Tracey Haybittle).
- **Smoke Signal:** wood-smoke "don't burn tonight" alerts.
- **Medicine Shortage Radar:** price concessions as an early signal of shortages.
- **Step-Free Live:** Metrolink lift outages and wheelchair users.
- **Easy Read Now:** late Easy Read versions of consultations.
- **Plan Checker:** unlawful wording in children's special-needs (EHCP) plans.
- **PQC Ready:** finding quantum-vulnerable crypto in small public bodies.
- **Agent Passport:** identities for AI agents.
- **Help Is Out:** silent telecare failures (PFD: Leonard Connell).
- **Locked Out:** a break-glass vault for key-safe codes (PFD: Derrick Tully).
- **Mule Shield:** students recruited as money mules.
- **FlashPoint:** surface-water flash-flood nowcasting.
- **Gap Call:** lone 999 callers between ambulance categories.
- **Sponsor Check:** is this visa sponsor real?

### 6.5 Avoid, or reinvent completely (crowded in past entries or 2026 repos)

- Safe or lit walking routes: at least five past entries and two winners.
- Disease prediction from symptoms or scans (about 30% of past projects); mental-health chatbots.
- Fake news, hate speech, deepfakes, phishing email; plain fraud classifiers with an LLM explanation.
- Crop yield, food donation, sign-language translation, traffic and parking.
- Flood, wildfire and satellite hazard alerts; plastic, lakes and water quality; carbon forecasting. **Sewage-spill forecasting is the exception: nobody tried it.**
- Anything needing blockchain, a GPU or a closed LLM. IBM said "We actually don't do any blockchain on Z."
- Public 2026 repos already cover transaction anomalies with LLM explanations (Z-Sentinel AI), verified sensor data for emergency routing (Project Syn), satellite hazard alerts (SkyGuardX) and flood warnings (FloodReady).

---

## 7. Spillcast: full build specification (default pick)

**One line:** Spillcast forecasts which storm overflows around Greater Manchester will spill sewage in the next six hours, and flags spills the rain cannot explain.

**Users and decisions:**
- *River users* (rowing clubs, open-water swimmers, paddlers, anglers): go in today or not?
- *Event organisers:* run or move the session.
- *Environment Agency or council officers:* where to sample, which spills to investigate.
- *Residents:* the river near me.

**Theme:** 1, Real-time AI for critical decisions. The tamper-evident evidence ledger adds Theme 2 depth.

### 7.1 Problem evidence (all sourced; links in section 14)

**Scale:**
- England's storm overflows spilled **450,398 times, for 3,614,428 hours, in 2024** (EA data via PA, 27 Mar 2025). The count was down 2.9% on 2023; the hours were a record high.
- **The River Irwell** (through Salford and the Quays) had **11,974 spills in 2023: 95 per mile, the highest rate of any English river** (Guardian analysis of EA data, reported by Salford Now).
- **Greater Manchester:** 816 United Utilities overflows logged **17,495 counted spills and 64,693 hours in 2025** (EA annual returns, our analysis).
- Manchester Central alone: 564 spills and 1,069 hours in 2025 at 38 sites (Top of the Poops, from EA returns), on the Irwell, Irk, Medlock, Black Brook and Moss Brook.

**Warnings are thin:**
- The EA's daily pollution risk forecasts covered **171 of 424** bathing waters in 2023, and the EA says the system does "**not specifically make predictions of sewage pollution**".
- A 2024 review in *WIREs Water* (Reading, Oxford and EA researchers) said forecast models "**are not keeping the public safe at most of the UK's 600-plus designated bathing water locations**". It recommended more sampling in storms, high-resolution rainfall predictions for local warnings, and **machine-learning** forecasting.

**Public maps only show the present:**
- The Rivers Trust map, Surfers Against Sewage and floodradar all show spills once they have started.
- The National Storm Overflows Hub (Water UK/Stream, launched Nov 2024) gives near-real-time status for all of England's ~14,000 overflows.

**Dry spills:** a BBC analysis cross-checking nine companies' spill data against Met Office rainfall suggested **nearly 6,000 possibly illegal dry-weather spills in 2022**.

### 7.2 Data (all downloaded or verified on 16 Oct; local copies in `data/spillcast/`)

**A. Spill events (labels):** the EA's "Event Duration Monitoring – Storm Overflow – Start/Stop Detailed Data".
- **Coverage:** one file per company per year, all 10 English companies, 2024 and 2025 (some 2026 files too). Open Government Licence; **not formally verified by the EA**.
- **Download URL pattern** (works):

  ```
  https://environment.data.gov.uk/api/file/download?fileDataSetId=c95ecc47-fa70-4a24-b8cc-098232987526&fileName=United%20Utilities%202024%20Detailed%20EDM%20Data.csv
  ```

  The 2025 file is the same with `2025`. Dataset page: https://www.data.gov.uk/dataset/event-duration-monitoring-storm-overflow-start-stop-detailed-data
- **Columns:** `Unique ID, Site Name, Discharge Start (GMT), Discharge Stop (GMT)`. The 2025 file adds empty trailing columns.
- **Date formats differ:**
  - 2024: `2024/01/01T20:00:00.000Z`
  - 2025: `2025-01-01T00:00:00.000Z`
  - Parse both with `pd.to_datetime(s.str.replace('/', '-'), utc=True, errors='coerce')`.
- **Row counts (what we found):**

  | Year | Activation rows | Overflows | Unparseable or negative rows |
  |---|---|---|---|
  | 2024 | 216,379 | 1,981 | 174 |
  | 2025 | 175,358 | 1,975 | 1 |

  These are **raw activations** (median length 16 minutes), not the EA's "12/24-hour counted spills".
- **Busiest days** (good replay candidates): 20 Sep 2025 (1,477 overflows started a spill), 1 Jan 2025 (1,608), 5 Dec 2024 (1,521), 16 Oct 2024 (1,450).
- **EA technical note:** column A is a unique ID that links to the annual returns; each row is one EDM activation.

**B. Overflow locations and metadata:** EDM annual returns 2025 layer (The Rivers Trust, from EA data).
- **Endpoint:** `https://services3.arcgis.com/Bb8lfThdhugyc4G3/ArcGIS/rest/services/Event_Duration_Monitoring_Storm_Overflows_2025/FeatureServer/0/query`
- **Fields we use:**
  - `UID`, `siteNameEA`
  - `Latitude`, `Longitude`
  - `recievingWaterName` (spelled this way in the source)
  - `edmOperationPercent`, `countedSpills`, `totalDurationAllSpillsHrs`
  - `localAuthority`, `bathingWater`
  - **Our local CSV has only these 10 fields.** The ArcGIS endpoint has 45 more, such as `siteNameWASC`, `treatmentType`, `wfdWaterbodyName` and `highSpillOperationalReview`; fetch them there with `outFields=*`
- **Paging:** 2,000 rows per query; use `resultOffset`.
- **United Utilities:** **2,270 overflows**. Our copy is `United Utilities overflows 2025 annual returns (Rivers Trust layer).csv`.
- **Greater Manchester** (`localAuthority` in Manchester, Salford, Trafford, Stockport, Tameside, Oldham, Rochdale, Bury, Bolton, Wigan): **816 overflows**.
  - 696 of them have 2025 event rows.
  - **82 monitors worked under 90% of the year**: drop or flag those.
  - 66 discharge to waters named "Irwell".
- **Join key:** `UID` = `Unique ID` = live-feed `Id` (format `UUP` plus 5 digits, e.g. `UUP02182`).

**C. Live status:** United Utilities storm overflow activity (via Stream / the National Storm Overflows Hub). Licence CC BY 4.0, credit "United Utilities storm overflow activity data".

```
https://services5.arcgis.com/5eoLvR0f8HKb7HWP/arcgis/rest/services/United_Utilities_Storm_Overflow_Activity/FeatureServer/0/query?where=1=1&outFields=*&f=json
```

- **Fields:** `OBJECTID, Id, Company, Status, StatusStart, LatestEventStart, LatestEventEnd, Latitude, Longitude, ReceivingWaterCourse, LastUpdated`.
  - Times are epoch **milliseconds**.
  - `Status=1` means spilling now and `0` not spilling. Check the other codes (such as offline) in the Stream docs.
- **Size and freshness:** **2,255 rows**. On 16 Oct at 21:16 UTC, 5 were spilling. United Utilities says it refreshes at least hourly; floodradar polls every 15 minutes.
- **Paging and legal context:** 2,000 rows per query, so page with `resultOffset`. The Environment Act 2021 s.81 requires publication within an hour of a discharge starting.

**D. Rain (features):** Open-Meteo. Free for non-commercial use, CC BY 4.0; credit "Weather data by Open-Meteo.com".
- **History** (for training):

  ```
  https://archive-api.open-meteo.com/v1/archive?latitude=53.48,53.50&longitude=-2.24,-2.30&start_date=2024-01-01&end_date=2025-12-31&hourly=precipitation&timezone=UTC
  ```

  The API accepts comma-separated lists of coordinates. ERA5/ERA5-Land "best match", about 9–25 km cells.
- **Live and forecast:**

  ```
  https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&hourly=precipitation&past_days=2&forecast_days=2&timezone=UTC
  ```

- **Better train/serve consistency (optional, verify first):** the historical-forecast API (archived model forecasts) lets training use the same kind of input the live system gets.
- **Rate limits:** under 10,000 calls a day, 5,000 an hour, 600 a minute. Group overflows into ~0.1° cells: Greater Manchester needs roughly 30–60 cells, so a handful of calls.
- **Optional upgrade:** EA rain gauges.
  - Real-time flood-monitoring API: `https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=rainfall`. 15-minute readings, about 4 weeks retained.
  - Hydrology API for quality-checked history: `https://environment.data.gov.uk/hydrology/doc/reference`.

**E. Documents for RAG (download as text; government pages are OGL):**
- The EA's blog on bathing-water classifications and pollution risk forecasts.
- United Utilities' storm-overflow pages and FAQs.
- The EA guidance on event duration monitoring.
- A summary of the Storm Overflows Discharge Reduction Plan.
- The Environment Act 2021 duty to publish within an hour (s.81).
- Optionally, the Water UK / National Storm Overflows Hub explainer.

Keep 5–15 short documents. Cite each in `DATA_SOURCES.md`.

**pandas on s390x:** use CSV or NumPy `.npz`, **not parquet or feather**. pyarrow is not available on s390x.

### 7.3 Pipeline (implement in this order, verifying each step on the VM)

1. **Events.**
   - Load both United Utilities files (first four columns only).
   - Parse dates as above. Drop NaT rows and rows where stop < start.
   - Merge overlapping intervals per `uid`. Save `events_clean.csv`.
2. **Sites.**
   - Load the annual-returns CSV and filter to the 10 Greater Manchester boroughs.
   - Flag `edmOperationPercent < 90`.
   - Join event counts. Save `sites_gm.csv` (uid, name, lat, lon, river, edm_pct, bathing flag, 2024 spill hours).
3. **Rain cells.**
   - Snap each site to a 0.1° grid cell (`round(lat, 1), round(lon, 1)`), or the nearest cell centre.
   - Fetch hourly precipitation for 2024-01-01 → 2025-12-31 per unique cell. Cache to `rain_cells.csv`: a time × cell matrix of 17,544 hours.
4. **Hourly label matrix** per site over 17,544 hours:
   - `spilling[h]` = 1 if any event overlaps hour h.
   - `start[h]` = 1 if an event starts in hour h.
   - Store as `uint8` arrays in `.npz`.
5. **Samples.** For site s at hour t:
   - **Sequence input:** rain[t−47 … t] (48 hourly values) plus rain[t+1 … t+6] (6 values), so 54 steps. Channels: `rain_mm` and `is_future`.
     - In training, use observed future rain as the "forecast". To be honest about forecast error, optionally add multiplicative noise and say so.
   - **Static input:**
     - `spilling_now` (persistence; strong), `hours_since_last_spill_end` (capped)
     - the site's 2024 spill rate, `edm_pct`
     - month (sin/cos), hour of day (sin/cos)
   - **Label:** `y = 1` if any `spilling` in (t, t+6].
   - Also compute `y_start` = a new start in (t, t+6] given `spilling_now == 0`. This harder "new spill" task matters more for warnings; report both.
6. **Split.**
   - Train on 2024; validate on Nov–Dec 2024 or 10% of 2024; **test on 2025** (a temporal hold-out).
   - Optionally also hold out 15% of sites (a spatial hold-out).
7. **Sampling** (3 vCPU / 8 GB). Greater Manchester is ~700 sites × ~17.5k hours ≈ 12M samples.
   - Train on about **300–500k**: all positives near spill onsets plus random negatives, with class weights.
   - Evaluate on a uniform random sample of 2025 site-hours (correct base rate) and on all hours of the replay day.

### 7.4 Models (predictive half: mirrors IBM's fraud-LSTM lab)

**Baseline 1, a rule:** predict a spill if (past 6 h rain + next 6 h rain) > θ. Fit θ globally, then per site on 2024.

**Baseline 2, XGBoost 3.4.1** (in the image).
- Engineered features: rain sums over 1/3/6/12/24/48 h past and 1/3/6 h future, max hourly rain, `spilling_now`, hours since last spill, site stats.
- Export the booster as JSON or UBJ (portable across endianness).

**Main model, a Keras LSTM** (TF 2.18 in the image):

```python
seq_in = tf.keras.Input(shape=(54, 2), name="rain_seq")      # 48 past + 6 future hours; [rain_mm, is_future]
static_in = tf.keras.Input(shape=(N_STATIC,), name="static")
h = tf.keras.layers.LSTM(32)(seq_in)
h = tf.keras.layers.Concatenate()([h, static_in])
h = tf.keras.layers.Dense(32, activation="relu")(h)
out = tf.keras.layers.Dense(1, activation="sigmoid")(h)
model = tf.keras.Model([seq_in, static_in], out)
model.compile(optimizer="adam", loss="binary_crossentropy", metrics=[tf.keras.metrics.AUC(name="auc"), tf.keras.metrics.AUC(curve="PR", name="pr_auc")])
# class_weight={0:1, 1:w}, batch_size=1024, epochs 5–10, early stopping on val PR-AUC
model.save("spill_lstm.keras")
```

- Optionally calibrate on validation (isotonic) so outputs read as "62% chance of a spill in the next 6 h".
- **Metrics on 2025:**
  - ROC-AUC, PR-AUC, Brier score
  - recall at precision 0.8
  - **lead time**: median hours between the first alert (P > τ) and the actual spill start
  - false alarms per site-week
  - results split by `spilling_now`
  - Compare against both baselines in one table, and **say what failed and why** (judges reward it).
- **NNPA timing:** score **every Greater Manchester overflow (816) and every United Utilities overflow (2,255) in one `model.predict` batch**. Run it in graph mode, once with NNPA and once in a fresh process with `NNPA_DEVICES=0` (template in section 3.4). Save `evidence/nnpa_timing.csv`.
- **Optional:** a PyTorch twin on `torch_nnpa` for inference timing; a Snap ML tree model on NNPA.

### 7.5 Unexplained-spill audit (the "independent check")

- For each 2025 spill start, take the model's highest probability in the 6 hours before it, using observed rain.
- **Call a spill "unexplained" when:**
  - that probability is under 0.05, **and**
  - the 48 hours of rain before the start total under a stated threshold (e.g. 0.5 mm; state the rule), **and**
  - the site's monitor worked ≥ 90% of the year.
- Rank by duration. Show each case's rain chart, its probability timeline and its site history.
- **Language:**
  - Say "unexplained by rainfall: possible causes include groundwater infiltration, a blockage, a faulty monitor or an unpermitted discharge; needs checking".
  - **Never say "illegal".**
- Headline: the share of 2025 Greater Manchester spill hours that were unexplained, and the top 10 sites.

### 7.6 Generative half: Granite with RAG (mirrors IBM's loan lab)

**Model:**
- Granite 3.3 2B Instruct, **big-endian** GGUF. The Q4_K_M file is in the lab image; it can also be downloaded:

  ```
  https://huggingface.co/taronaeo/Granite-3.3-2B-Instruct-BE-GGUF/resolve/main/granite-3.3-2b-instruct-be.Q4_K_M.gguf
  ```

- Q8_0 (2.69 GB) may use the zDNN backend on z17, but **only through the lab image's `llama_cpp_python`**: the ghcr llama.cpp images have no zDNN. Benchmark both quants there.

**How to run it (pick one):**
- **Preferred:** `llama_cpp_python` inside the lab container (as the loan lab does). This is the only zDNN/NNPA-capable build. Or
- the llama.cpp server container, which gives an OpenAI-compatible local API:

  ```bash
  docker run -d --name llm --restart unless-stopped -p 127.0.0.1:8080:8080 -v ~/models:/models \
    ghcr.io/ggml-org/llama.cpp:server -m /models/granite-3.3-2b-instruct-be.Q4_K_M.gguf -c 4096 -t 3
  ```

  This server is CPU only (no zDNN). Call it with `httpx` (already in the image) rather than the `openai` package: judges "look at packages", and an `openai` dependency can read as a closed-API call.

**Retrieval:** `rank_bm25.BM25Okapi` over 300-word chunks of the section 7.2E documents (the loan lab's method). Return the top 3 chunks.

**Prompt 1, river outlook.**
- Inputs:
  - audience (rowers, swimmers, anglers or EA officer)
  - river name
  - the top 5 overflows by probability on that river, with probabilities and times
  - the rain forecast
  - the retrieved guidance
- Output JSON: `{risk_level, headline, advice[], sources[]}`, at most 150 words. Use only the facts given.

**Prompt 2, evidence note for an unexplained spill.**
- Inputs: a facts table (start, duration, rain in the previous 48 h, the model's probability, monitor %, site history).
- Output: what happened, possible causes, what to check, sources. No legal conclusions.

**Speed:** design for a few tokens per second.
- `max_tokens` ≤ 200; call the model only for flagged items; cache by `(river, hour)`.
- Show a "generated by Granite on LinuxONE" label.
- Measure tokens per second for the deck by timing `llama_cpp_python` generations in the lab image (NNPA-capable build). `llama.cpp:full --bench` gives CPU-only numbers; label them as such.

### 7.7 Security layer (LinuxONE strengths, Theme 2 depth)

**Postgres 17 on a LUKS2 volume** (CPACF-accelerated AES-XTS):

```bash
fallocate -l 4G ~/vault.img
sudo cryptsetup luksFormat --type luks2 -c aes-xts-plain64 -s 512 ~/vault.img
sudo cryptsetup open ~/vault.img vault && sudo mkfs.ext4 /dev/mapper/vault
sudo mkdir -p /srv/vault && sudo mount /dev/mapper/vault /srv/vault
# postgres:17 container with -v /srv/vault/pg:/var/lib/postgresql/data and -p 127.0.0.1:5432:5432
```

Screenshot `sudo cryptsetup luksDump ~/vault.img` and `lsblk`.

**Tamper-evident evidence ledger:**
- Each ingested live record and each forecast is appended with `hash_i = SHA256(hash_{i-1} || canonical_json(record))`.
- Every N minutes, sign the chain head with **ML-DSA-65** (post-quantum) using OpenSSL 3.5 in a `debian:trixie` container: `openssl genpkey -algorithm ML-DSA-65 -out ledger_key.pem`, then `openssl pkeyutl -sign …`.
- Add `GET /api/ledger/verify`. **Demo:** edit one database row and verification fails.
- Why it matters: spill data can be revised, and regulators need evidence-grade records.

**Network:**
- iptables default-deny apart from 22 and the app port.
- Internal services bound to `127.0.0.1`.
- A custom Jupyter token.
- Optional TLS via a Caddy container, plus a post-quantum handshake demo (`openssl s_server -groups X25519MLKEM768` in trixie).

**The pitch line:** "What trust are we protecting, and from whom? The public record of when sewage entered the river, protected against quiet revision."

### 7.8 Serving, UI and live loop

**Run the API in a container.** Simplest is a `Dockerfile` `FROM registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest` that adds `pip install fastapi uvicorn`. The image already has TF, XGBoost and llama-cpp. Run it with `docker compose` alongside `postgres:17` and, optionally, `llama.cpp:server`. That gives containerisation evidence.

**Scaling evidence:**
- Add a `proxy` service (caddy or nginx; both have s390x images). It is the only service that publishes port 8000, and it forwards to `api:8000`.
- Give `api` an `expose: ["8000"]` entry and no `ports:`.
- Then `docker compose up -d --scale api=2` works. Without the proxy, a second replica can't bind the same host port.

**Database driver:**
- psycopg2 has no s390x wheel, so pip would try a source build.
- Use pure-Python **`pg8000`**, or `psycopg` 3 with libpq installed.
- Or keep it simple with **SQLite** (Python standard library) stored on the LUKS volume.

**Data credits in the UI:** show them in the page footer, not only in `DATA_SOURCES.md`:
- "United Utilities storm overflow activity data" (CC BY 4.0)
- "Weather data by Open-Meteo.com" (CC BY 4.0)
- "Contains Environment Agency data" (OGL)
- "The Rivers Trust, from EA data"

**Endpoints:**

| Endpoint | Returns |
|---|---|
| `GET /api/overflows` | GeoJSON: id, name, lat, lon, river, status_now, p_spill_6h, updated |
| `GET /api/overflow/{uid}` | 48 h history, rain past and forecast, probability curve |
| `GET /api/outlook?river=&audience=` | Granite outlook |
| `GET /api/audit` | Unexplained spills |
| `GET /api/metrics` | Back-test results and NNPA timing |
| `GET /api/ledger/verify` | Ledger check result |
| `GET /api/replay?date=2025-09-20` | Hourly snapshots for the replay day |

**Front-end:** one `index.html` with Leaflet 1.9.4 and Chart.js from a CDN.
- Markers coloured by 6-hour risk; a side panel with the outlook and charts.
- A replay time slider for 20 Sep 2025; an "Audit" tab.

**Worker loop**, every 15 minutes (as a thread or a compose service):
1. Fetch the live feed, paging with `resultOffset`.
2. Fetch the rain forecast for the cells.
3. Build the sequences and score them in one NNPA batch.
4. Write to Postgres and append to the ledger.
5. Log the latency.

**Serving:** uvicorn on `0.0.0.0:8000`, with iptables opening 8000. URL: `http://148.100.78.95:8000`.

### 7.9 Repository layout (public GitHub repo; judges read commit history)

```
spillcast/
  README.md               # problem, data+licences, architecture, how to run on LinuxONE, results, choices/rejections, failures+fixes, team roles, next steps, open-source list
  DATA_SOURCES.md         # every dataset/document with URL, licence, credit line
  docker-compose.yml      # proxy (caddy/nginx, only public port), api (scalable), worker, db (postgres:17 or SQLite file), llm (optional)
  Dockerfile              # FROM the L1CC lab image + fastapi/uvicorn
  .gitignore              # data/, *.pem, .env, *.gguf, *.img
  src/spillcast/
    config.py  data_edm.py  data_sites.py  data_rain.py  labels.py  features.py
    train_baselines.py  train_lstm.py  benchmark_nnpa.py  audit.py
    rag.py  llm.py  ledger.py  live.py  api.py
  web/  index.html  app.js  style.css
  notebooks/  01_eda.ipynb  02_train_eval.ipynb  03_nnpa_benchmark.ipynb
  evidence/   probe.txt  nnpa_timing.csv  metrics.json  screenshots/*.png
  scripts/    setup_vm.sh  open_ports.sh  luks_setup.sh  fetch_data.sh
```

### 7.10 Demo, deck and video for Spillcast

**3-minute video:**
1. **0:00–0:20.** "The Irwell had 11,974 sewage spills in 2023, the worst rate per mile in England. Nobody warns you before it happens." Show a river-user quote.
2. **0:20–0:40.** Data on screen with licences: EA spill records, United Utilities live feed, Open-Meteo rain.
3. **0:40–1:50.** Live map of every overflow coloured by 6-hour risk. Replay 20 Sep 2025: the 09:00 forecast against the spills that started by 15:00. Granite's outlook for rowers on the Irwell. One unexplained dry-weather spill with its evidence note.
4. **1:50–2:30.** IBM Z proof:
   - the terminal showing `uname -m` → s390x, the `lscpu` NNPA line and the server IP (judges check IPs in videos)
   - `docker compose ps`
   - the NNPA vs CPU timing table, and AUC/lead time against the baselines
   - `cryptsetup luksDump`, and the ledger tamper test
5. **2:30–2:50.** What we rejected and why, what broke and how we fixed it, what's next (EA or water-company pilot; all England companies).
6. **2:50–3:00.** The whole team, one line each.

**Deck (10–12 slides):**
1. Title and team with roles
2. Problem plus one sourced local number
3. Who decides what (users)
4. Data and licences
5. Architecture with the LinuxONE boundary (predictive + generative, the loan-lab pattern)
6. Model comparison table
7. Results: back-test, lead time, failures
8. **Proof it runs on LinuxONE** (s390x, IP, `pip list`, NNPA timing)
9. Security (LUKS, ledger, token, iptables)
10. Demo screenshots plus video and repo links/QR codes
11. Impact and next steps
12. Learnings

**Deck rules:**
- Keep the organiser's headings: "Wow factor", "Learnings", "Let's jump into the demo".
- Never leave the demo slide empty: judges read the PDF on its own.

### 7.11 Risks and fallbacks

**Data and modelling:**
- **9–25 km rain cells miss summer cloudbursts.** Add the nearest EA gauge as a feature if time allows, and state the limitation.
- **Persistence makes the task look easy.** Always report the harder "new spill when not spilling now" metric.
- **Train/serve mismatch** (reanalysis vs forecast rain). Note it; try the historical-forecast API; add noise in training.
- **Monitor faults.** Filter on `edm_pct ≥ 90`.

**Live operation:**
- **A dry weekend means few live spills.** The replay and the 2025 back-test carry the demo.
- **The live feed is down.** Cache the last snapshot and show its timestamp.

**Platform:**
- **Granite is slow.** Pre-generate outlooks for the demo river; cache.
- **Memory on the 8 GB VM.**
  - Load Granite in exactly one process.
  - Before recording the demo or a load test, shut down notebook kernels (or stop the `notebook` container).
  - Check with `docker stats; free -h`.
- **Not enough time:** the minimum viable path, in order:
  1. Back-test LSTM vs baselines
  2. NNPA timing
  3. Map with replay
  4. One Granite outlook
  5. LUKS screenshot
  - The ledger and live loop are bonuses.

---

## 8. Alternative ideas: build summaries (full write-ups in `research/00_prep_doc_export_16Oct.md`)

### 8.1 Cable Watch (working name "Snag": "catch the anchor before it catches the cable"). Theme 1, plus a Theme 2 identity layer

**Pitch:** spot ships behaving as if they are dragging an anchor, or hiding who they are, near subsea power and internet cables, and alert the coastguard and cable operator while there is still time to act.

**Evidence:**
- **25 Dec 2024:** Estlink 2 (658 MW) and telecom cables in the Gulf of Finland were damaged; the tanker Eagle S left an anchor drag line of about **100 km**.
- **Nov 2024:** two Baltic cables were cut while a nearby ship's AIS went dark for 7.5 hours.
- **Shetland, Oct 2022:** two breaks cut phones and broadband; residents were told to try any phone to reach 999.
- **UK exposure:** 64 cables; no UK-owned repair ship; a 2025 parliamentary committee called the government "too timid".
- **Global:** 150–200 cable faults a year (ICPC); 80% from fishing and anchoring (ITU).
- **Local hook:** the 1,400 MW North Sea Link lands at Cambois, near Blyth.

**Data:**
- **Digitraffic** (Fintraffic, Baltic, CC BY 4.0, no key):
  - REST `https://meri.digitraffic.fi/api/ais/v1/locations` and `/api/ais/v1/vessels`
  - MQTT over WebSocket `wss://meri.digitraffic.fi:443/mqtt`, topics `vessels-v2/<mmsi>/locations`, `vessels-v2/<mmsi>/metadata` and `vessels-v2/status`
  - Its docs show live data only: **record the stream from kick-off**.
- **aisstream.io** (UK waters): WebSocket, GitHub sign-in, a bounding box is required, 3 connections per account, no replay.
- **EMODnet** cable routes (free to reuse with credit).
- **Danish Maritime Authority** historical AIS: daily CSVs, Danish waters only; you may not combine it to identify individuals.
- No public labels for anchor drags exist: **simulate drags injected into real tracks, and say so.**

**AI:**
- An LSTM over per-ship position sequences scores the anchor-drag pattern. Features: speed, heading/course difference, turn rate, distance to cable, slowing over a cable while "under way". Time it on NNPA, exactly like the fraud lab.
- An Isolation Forest flags unusual behaviour.
- Identity checks: name or flag changes, MMSI reuse, impossible position jumps.
- Granite writes the alert: what was seen, which cable, the ship's history, a suggested first call.

**Edge over rivals (NKT, Vesper Marine, Nordic Warden, Space Data):**
- Behaviour, not geofences.
- It catches anchors dragged while the ship is still *under way*, which rules keyed to "at anchor" status can miss.
- Open data and public interest.

**Demo:**
- Open on Christmas Day 2024.
- Live ships with cables overlaid.
- Replay an injected drag: the alert fires before the ship reaches the cable.
- Show the false alarms per 1,000 ship-hours and the messages per second scored on s390x.

### 8.2 Memory Lane (the abstract the team was advised to submit). Theme 1, plus a Theme 2 vault

**Pitch:** turn what a family knows about a person with dementia into a ranked search map within seconds of a missing report, then keep the search honest about which ground has been covered.

**Evidence:**
- **Scale:** at least 40,000 people with dementia go missing for the first time each year in England and Wales (Portsmouth review, citing NPIA 2011).
- **Time matters:** 72% of those found alive were found by the next day; only 20% of those not found until day five or later were alive. Those who died were usually found *closer* to where they were last seen.
- **UCL 2026 study** of 1,540 incidents involving people aged 65+: 27% involved dementia; 9.4% of those caused serious harm; risk rose at night and after 24 hours; 78% went missing from home; 30% were repeats.
- **The Herbert Protocol** (the GMP scheme) is a paper form kept at home.
- **2026 coroners' reports** (young people, not dementia) found no search adviser on duty overnight, and searched fields recorded inaccurately.

**What we'd build:**
1. Granite (on the VM) extracts routines, familiar places, past addresses and previous found locations from a guided chat into a JSON "living Herbert Protocol". Places are geocoded and stored encrypted.
2. A break-glass unlock with an incident number. Every access goes to a tamper-evident log, and the family is notified.
3. A probability map on a 50 m grid. Inputs: distance decay, familiar places and routes, OpenStreetMap hazards (water, ditches, woodland edges, rail) and urgency (temperature, darkness, hours missing).
   - **For the chip:** a small neural net scores the grid cells, trained on simulated cases from published lost-person distance statistics. Compile it for NNPA and say the cases are simulated.
4. Live Bayesian updates as search teams clear sectors (with a probability of detection).
5. An Isolation Forest flags misuse of the vault.

**Data:**
- OpenStreetMap; Ordnance Survey Open Names, Roads and Greenspace (OGL).
- Met Office or Open-Meteo weather; NHS dementia diagnosis statistics.
- A case set of 30–50 public UK news reports (last seen vs found).
- Koester's ISRID distance tables.

**Key line:** "IBMGER002 detects that someone is getting lost; we find someone already missing, with no tracker."

### 8.3 Proof of Kin. Theme 2, plus a Theme 1 payment decision

**Pitch:** verify that a message really comes from the relative it claims to be, using writing style and shared memories, and let the bank pause a payment **without ever seeing the chat**.

**Evidence:**
- Joe (judge) explicitly asked for this.
- Starling: 28% of UK adults targeted by AI voice-cloning scams in a year; 46% had never heard of the threat; 8% would send what was asked; 3 seconds of audio can clone a voice.
- UK fraud losses topped £1.1bn in 2024 (UK Finance).
- Visa: 15% of UK people targeted by "Hi Mum" scams.

**Build:**
1. A per-contact style fingerprint (character n-grams, punctuation, emoji, greetings and sign-offs, plus a small style-embedding model on NNPA), kept on the device and encrypted.
2. Claim detection ("new number", "it's me").
3. Three signals fused into one risk with reasons: scam intent (urgency, secrecy, payment), style match and knowledge checks (e.g. "doesn't use your name").
4. Granite writes a challenge from a shared-memory vault and checks the answer by meaning.
5. The bank receives only an **ML-DSA-signed "kin-risk" token** (OpenSSL 3.5 PQC) and holds the payment.
6. Granite also plays the attacker, generating impostor messages to stress-test the detector.

**Data:**
- The UCI SMS Spam Collection.
- 50–100 cited impersonation scripts (banks, Which?, Action Fraud).
- Consented teammate chats, kept on the encrypted volume only; synthetic chats for evaluation.
- Sparkov transactions (CC0) for the payment model.

**Key line:** "We verify the sender, not the content."

### 8.4 Lights Out, Lives On (now with real outage history). Theme 1

**Pitch:** when the power fails, rank which households (or streets) hold people who depend on electricity to stay alive, and estimate when each is in danger, so welfare checks go there first.

**Evidence:**
- 2026 coroners' reports: Janette Palmer (a supported-living block missing from the Priority Services Register); Peter Coates (a man on mains-powered breathing equipment alone in a power cut).
- Ofgem's Storm Arwen study: 2.5–11 days without power, and most people on the register recalled no proactive contact.
- Which?: digital landlines and telecare fail in power cuts.

**Data:**
- **Electricity North West "Unplanned Outages"** (the Greater Manchester network operator): every unplanned outage since 2000, with location, time, duration and cause where known.
  - JSON, CSV or Shapefile from `electricitynorthwest.opendatasoft.com`, listed at https://www.opennetzero.org/electricity-north-west/unplanned-outages1.
  - **Registered users only**; licence not stated.
- Live faults: ENWL's power-cut map (check its API); NGED and UKPN live feeds for other regions.
- Census 2021 (aged 75+ living alone, disability), the CQC care-home directory, Ofcom mobile coverage, and Met Office or Open-Meteo temperature.
- The Priority Services Register is confidential: use a synthetic household list for the demo.

**AI:**
1. A model on the chip predicts how long a new outage will last, from its cause, place, time, season and weather.
2. Rank households by "hours until harm": for example, an oxygen concentrator's battery life against the predicted outage length, or cold exposure.
3. Re-rank live as power is restored.
4. Granite drafts welfare-call scripts and a situation report.

**Don't use** the Kaggle "Electrical System Fault Diagnosis" dataset. It holds rotor and stator measurements of electrical machines (motor/generator faults), not who loses power or for how long.

### 8.5 Other sketches

- **Ember** (Theme 3, plus a Theme 2 referral). Send fire-safety visits where emollient-cream and smoking fire deaths are likely.
  - *Evidence:* a coroner found fire services count 50 emollient deaths since 2020 against 15 on the medicines regulator's record (PFD: James Rownsley); a 2026 South Shields case (PFD: Malcolm Campbell).
  - *Data:* OpenPrescribing emollient volumes per GP practice; smoking prevalence; deprivation; fire statistics.
  - *AI:* an area risk model; Granite rebuilds the missing death count from coroners' reports and news.
  - *Weak spot:* monthly, area-level data.
- **Mule Ring Radar** (Theme 2). Three bank containers find a cross-bank money-mule ring using private set intersection or Paillier (`phe` works on s390x).
  - *Data:* IBM's synthetic AML transactions (CDLA-Sharing).
  - *Edge:* nobody built PSI or MPC in 2025.
  - *Weak spot:* the demo is abstract. Check prior art such as the BIS Innovation Hub's Project Aurora.
- **Martha's Voice** (Theme 1). Fuse a family's free-text concern ("he's not right") with NEWS2 vital-sign trends, routed through the Martha's Rule escalation pathway.
  - *Data:* PhysioNet 2019 sepsis challenge vitals (check the licence) plus synthetic concern text.
  - *Weak spot:* the concern text is synthetic, and clinical claims need care.
- **Shell Alarm** (Theme 2). Watch the Companies House Streaming API (free key) for companies registered at strangers' homes, and draft the victim's removal request.
  - *Evidence:* 10,387 applications to remove a disputed registered address in 2021–22 (Which?); 16 addresses on one Worksop street used in one weekend (NRLA).
  - *Weak spot:* director ID checks since late 2025 may already cut this.

---

## 9. LinuxONE software compatibility (s390x, big-endian). Full detail in `research/04_linuxone_technical_reference.md`

### 9.1 Where to get packages, in order of preference

1. **The L1CC lab image** (section 3.2): everything heavy is compiled. `pip install` pure-Python extras on top.
2. **Ubuntu 24.04 `apt`.** Use a venv with `--system-site-packages`; Ubuntu enforces PEP 668.
3. **s390x wheels that exist on PyPI:** tokenizers, safetensors, pydantic-core (so FastAPI works), snapml, pymongo, confluent-kafka, regex, pyyaml, aiohttp, websockets, zstandard, xxhash, cffi, protobuf, ruff, uv.
4. **PyTorch CPU wheels for s390x** from `download.pytorch.org`. No torchvision or torchaudio wheels.
5. **A `debian:trixie` container**, which has s390x packages Ubuntu lacks:
   - onnxruntime 1.21, faiss 1.11, torchvision 0.21
   - **OpenSSL 3.5** (post-quantum)
   - pgvector 0.8
6. **The IBM Z container registry** `icr.io/ibmz/…`: AI toolkit images (TF, PyTorch, Triton, Snap ML, zDLC). Needs a free IBM Cloud API key.

**pip has no s390x wheels for:** numpy, scipy, pandas, scikit-learn, pillow, pyarrow, grpcio, cryptography, onnxruntime, opencv, faiss, spaCy or **psycopg2** (use `pg8000`, apt `python3-psycopg2`, or SQLite). pip will attempt slow or failing source builds, so get these from the image or apt.

### 9.2 Safe stack

| Layer | Use |
|---|---|
| ML/DL | XGBoost, scikit-learn, TF/Keras (+ zDNN), PyTorch (+ torch_nnpa) from the lab image; Snap ML |
| LLM | llama.cpp: the lab image's `llama_cpp_python` (built with zDNN, so NNPA-capable), or `ghcr.io/ggml-org/llama.cpp:server` / `:full` (CPU and OpenBLAS only, no zDNN). Big-endian Granite GGUF from Hugging Face `taronaeo/*-BE-GGUF`. Faster fallback: Granite-3.0-1B-A400M-BE |
| RAG | `rank-bm25` (in the image). sentence-transformers works on top (safetensors). Vectors in numpy, `hnswlib` (apt) or pgvector |
| API/UI | FastAPI + uvicorn; plain HTML/JS with Leaflet and Chart.js; nginx or Caddy |
| Data | `postgres:17`, `redis` (Docker Hub s390x images exist) |
| Monitoring | Prometheus (Docker Hub); Grafana's s390x tarball or `icr.io/ibmz/grafana` |
| Containers | Docker CE + compose plugin (s390x); podman |
| Base images with s390x | `python:3.12-slim`, `python:3.13-slim-trixie`, `debian:trixie`, `ubuntu:24.04`, `postgres:17`, `redis`, `nginx`, `caddy`, `prometheus`, `aquasec/trivy` |

### 9.3 Avoid

- **Runtimes and orchestration:**
  - Ollama (no s390x build)
  - vLLM (hours of experimental source building)
  - k3s and kind (no s390x)
- **Data stores and pipelines:**
  - MongoDB (no s390x community build or image); use Postgres JSONB.
  - Redpanda, and the `apache/kafka` image (there is `icr.io/ibmz/kafka`).
  - chromadb; faiss from pip.
- **Python libraries:**
  - **Streamlit** (needs pyarrow); **pyarrow, polars and DuckDB**, so no parquet: use CSV or `.npz`.
  - spaCy, and therefore Presidio.
  - librosa, openai-whisper, faster-whisper, vosk and pyod (they need numba or binaries with no s390x build).
- **Toolchains:**
  - IBM HElayers and OpenFHE.
  - Anaconda and Miniconda (s390x support ended 31 Mar 2025); conda-forge.
- **Platform features that don't exist on these VMs** (roadmap slide only):
  - Secure Execution (it needs KVM; our VM runs under z/VM)
  - Hyper Protect
  - Crypto Express secure keys
  - Spyre cards
- **Docker images with no s390x build:** `python:3.12-slim-bookworm`, `node:22`, `grafana/grafana`.

### 9.4 Big-endian pitfalls

- GGUF files must be the **-BE** variant, or converted with `convert_hf_to_gguf.py --bigendian`. A little-endian file fails with "GGUF file version 50331648 is extremely large… endianness?".
- Prefer **safetensors** (it byte-swaps), ONNX, PMML or XGBoost JSON/UBJ. Don't move pickled sklearn or joblib models between architectures: **retrain on the VM**.
- For raw binaries and memory-mapped arrays, declare the byte order (`'<f4'`). Build indexes on the VM.
- Validate a few predictions against a laptop. A 2024 team got nonsense from BERT until they fixed byte order.
- Compile flags: `-march=z16` code runs on our z17; `-march=z17` code only runs on z17.

### 9.5 Security features you can demonstrate

| Feature | How |
|---|---|
| CPACF hardware crypto | `openssl speed -evp aes-256-gcm`; `cryptsetup benchmark -c aes-xts-plain64 -s 512`; `sudo apt install libica-utils && icainfo` |
| LUKS2 encrypted volume | See section 7.7. Screenshot `luksDump` and `lsblk` |
| Post-quantum TLS and signatures | `docker run -it debian:trixie bash -c "apt-get update && apt-get install -y openssl && openssl list -kem-algorithms && openssl list -signature-algorithms | grep -i ml-dsa"`. OpenSSL 3.5 has ML-KEM, ML-DSA and SLH-DSA, with X25519MLKEM768 as its default keyshare. Ubuntu 24.04's OpenSSL 3.0 does not |
| Image scanning | `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image <img>` |
| Privacy tech | diffprivlib, Opacus, `phe` (Paillier). Hand-rolled FedAvg (Flower needs grpcio and cryptography builds) |
| Network | iptables default-deny; `127.0.0.1` binds; custom Jupyter token; SSH tunnel |

**Production analogue to cite:** Machine Learning for IBM z/OS scores fraud inside CICS transactions on z17 (IBM cites up to 282k transactions per second). It is z/OS only, not available to us.

---

## 10. Pitch, video, README and submission

### 10.1 Three-minute video blueprint (any idea)

1. **0:00–0:20.** A real person or a teammate's story, then the headline number.
2. **0:20–0:40.** The problem, why it's unsolved, and the data on screen with licences.
3. **0:40–1:50.** The **live demo**; the "wow" moment lands in this minute. Record it in a browser whose **address bar shows `http://148.100.78.95:<port>`**, not localhost through a tunnel: judges look at IP addresses in videos.
4. **1:50–2:30.** **How it runs on IBM Z.** Show the architecture, then the terminal:
   - `uname -m` → s390x, the `lscpu` NNPA line and **the server IP** (judges match IPs)
   - `docker ps`
   - the NNPA vs CPU timing; the encrypted volume or post-quantum handshake
   - which IBM lab pattern each model follows
5. **2:30–2:50.** One thing you rejected, one thing that broke and how you fixed it, next steps.
6. **2:50–3:00.** Everyone on screen.

**Video rules:**
- Every member speaks; nobody dominates.
- Burn in subtitles.
- Stay under 3:00.
- Never show the IP together with a token or key in the same frame.

### 10.2 README must cover

- Problem
- Data and licences
- Architecture
- How to run it on LinuxONE (exact commands)
- Results and metrics
- Choices and rejected options
- Failures and fixes
- **Team roles (who did what)**
- Next steps
- Every open-source library and model, with links

### 10.3 Submission checklist (Hack2Skill)

- [ ] **Submitted by the registered team leader** (only the leader can submit)
- [ ] Title `[<Team Name>_IBM Z Datathon 2026 Project]`, adding the team number if the form asks (the hosting guide's example is `[ONLXXX]`)
- [ ] Video ≤ 3:00, with the LinuxONE instance, IP and model visible
- [ ] Public GitHub repo link, with commits from every member
- [ ] Deck PDF that stands on its own; no empty demo slide
- [ ] Screenshots uploaded: probe, labs, containers, security, NNPA timing, scaling
- [ ] Open-source list
- [ ] Optional flowchart
- [ ] Submit by 09:30–10:00 Sun; screenshot the confirmation
- [ ] **After submitting, keep everything running.** Don't stop or delete the VM, app, repo or evidence. Judges may come back and ask a team to prove it ran on LinuxONE, and projects may be shown at the closing ceremony. Keep it live at least until winners are announced on 28 Oct (the VM lasts 30 days)

### 10.4 Evidence checklist (capture during the build)

- [ ] All four lab notebooks finished (screenshots)
- [ ] Probe output: s390x, Big Endian, machine type 9175, the `nnpa` flag, 3 vCPU
- [ ] `docker compose ps`; images with `Architecture=s390x` (`docker image inspect -f '{{.Architecture}}' <img>`)
- [ ] Model latency on CPU vs NNPA (median and p95/p99); LLM tokens per second
- [ ] CPACF `openssl speed`; `cryptsetup luksDump`
- [ ] Optional: post-quantum handshake (`X25519MLKEM768`) and an ML-DSA certificate
- [ ] iptables rules; the custom Jupyter token
- [ ] A Trivy scan of the api image (`aquasec/trivy image <img>`)
- [ ] Optional: `docker compose up --scale api=2`, with a load test from a laptop

---

## 11. Team roles and teamwork evidence (judges mark it)

| Role | Owns |
|---|---|
| Platform lead | VM, Docker, Granite server, encryption, post-quantum, scaling, evidence screenshots |
| Data lead | Datasets and licences, cleaning, models, the headline metric |
| Connector note | **Only the registered Hack2Skill team leader can submit.** The Connector must be the leader, or the leader must be awake and logged in by 09:15 Sunday |
| App lead | API, map UI, live updates, demo flow |
| Story lead | Deck, 3-minute script, video edit, testimonial |
| Connector | Timeboxes, GitHub hygiene, the README "who did what", the Hack2Skill submission |

With four people, pair Platform with GenAI and Story with Connector.

**Showing teamwork:**
- Everyone commits under their own GitHub account.
- Add every member's public SSH key to the VM.
- Everyone appears in the video.

---

## 12. Open questions (ask in Discord #helpdesk or the IBM Z SME channel)

- [ ] Is the Z Xplore **Concepts badge** required for prizes? For every member, or one per team?
- [ ] The exact final submission time on Sunday (10:00 vs 11:00 vs 11:30)
- [ ] May the final project differ from the submitted abstract?
- [ ] Is a public demo URL on our VM allowed? Which ports?
- [ ] May we pull IBM AI Toolkit images from `icr.io`?

---

## 13. What is in this bundle

| Path | What |
|---|---|
| `CLAUDE.md` | Short project memory for Claude Code (loads automatically) |
| `HANDOFF.md` | This file: the authoritative brief |
| `research/00_prep_doc_export_16Oct.md` | The full team prep doc (ideas, abstracts, evidence links, run sheet, roles, pitch blueprint) as of 16 Oct |
| `research/01_overlap_with_2025_projects.md` | How each idea overlaps the 481 projects from 2025, plus a census of privacy tech used |
| `research/02_*`, `research/03_*` | Deep profiles of the 2025 global and hub winners' decks, with lessons |
| `research/04_linuxone_technical_reference.md` | s390x package matrix, containers, NNPA, LLMs, security, evidence (14 Oct; the VM size there is outdated) |
| `research/05_open_data_catalog.md` | About 90 verified open datasets and APIs, with licences and limits |
| `research/06_problem_evidence_34_candidates.md` | 34 evidence-backed problem candidates (coroners' reports, regulators) |
| `research/07_past_datathon_winners_2021_2025.md` | Every known past IBM Z Datathon winner and gallery; judge commentary |
| `research/08a`–`08e` | Detailed notes on the six pre-event sessions (orientation, keynote and winners, AI on Z, trust and identity, how to win) |
| `research/09_other_hackathon_winners_patterns.md` | 25 winners from other hackathons and the patterns they share |
| `transcripts/` | Raw transcripts: 16 Oct technical enablement, 17 Oct kick-off keynote, 17 Oct judges' panel, 17 Oct logistics, and the six prep sessions |
| `reference/` | IBM `jupyter-lab-ml` README, RHEL README and packages list; the four lab notebooks; the L1CC deployment guide |
| `data/IBM_Z_Datathon_2025_classified.csv` | All 481 projects from 2025: area, closest 2026 theme, AI, data, novelty 1–5, one-line summary |
| `data/2025_deck_texts.zip` | Extracted text of every 2025 deck (OCR for image-only decks) |
| `data/spillcast/` | United Utilities 2024 and 2025 spill events (EA, OGL), overflow coordinates (Rivers Trust/EA), the EA technical note, and a README with URLs |

The team's original files (guidebook docx, Manchester instructions, emails, the 2025 decks and spreadsheet) sit in the parent folder `research datathon/` on Muhammad's laptop.

---

## 14. Key sources

**Platform and labs:**
- https://github.com/linuxone-community-cloud/jupyter-lab-ml
- https://github.com/linuxone-community-cloud/technical-resources (deployment guide: `faststart/deploy-virtual-server.md`)
- L1CC portal: https://linuxone.cloud.marist.edu/#/login
- llama.cpp on s390x: https://github.com/ggml-org/llama.cpp/blob/master/docs/build-s390x.md
- zDNN backend: https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/zDNN.md
- Big-endian models: https://huggingface.co/collections/taronaeo/s390x-verified-models-672765393af438d0ccb72a08
- IBM Z container registry: https://ibm.github.io/ibm-z-oss-hub/main/main.html
- IBM TF/PyTorch accelerators: https://github.com/IBM/ibmz-accelerated-for-tensorflow · https://github.com/IBM/ibmz-accelerated-for-pytorch
- zDLC: https://github.com/IBM/zDLC
- OpenSSL 3.5 notes: https://github.com/openssl/openssl/blob/openssl-3.5/NEWS.md

**Spillcast:**
- EA spill events: https://www.data.gov.uk/dataset/event-duration-monitoring-storm-overflow-start-stop-detailed-data
- Annual returns layer: https://services3.arcgis.com/Bb8lfThdhugyc4G3/ArcGIS/rest/services/Event_Duration_Monitoring_Storm_Overflows_2025/FeatureServer/layers
- 2024 totals: https://www.hellorayo.co.uk/hits-radio-chilled/uk/news/sewage-spilled-last-year
- EA on its 2024 data: https://www.gov.uk/government/news/environment-agency-storm-overflow-spill-data-for-2024
- Irwell: http://www.salfordnow.co.uk/2024/04/02/almost-12000-spills-of-sewage-recorded-in-the-river-irwell-last-year-these-figures-are-shocking/
- Manchester Central figures: https://www.top-of-the-poops.org/constituency/manchester-central
- EA pollution risk forecasts: https://environmentagency.blog.gov.uk/2024/02/23/bathing-water-classifications-and-short-term-pollution/
- Forecast review: https://www.thewaterreport.co.uk/single-post/sewage-spill-forecasting-methods-not-up-to-the-job
- Dry spills: https://farming.co.uk/news/defra-coverage-of-bbc-investigation-into-potential-illegal-dry-spills-by-water-companies-in-2022
- National Storm Overflows Hub: https://www.thewaterreport.co.uk/single-post/national-near-real-time-storm-discharge-data-goes-live
- floodradar: https://www.floodradar.co.uk/overflow/fleet-street-uup00745
- StormHarvester: https://emerald.vc/portfolio/stormharvester
- Open-Meteo: https://open-meteo.com

**Cable Watch:**
- Eagle S: https://en.wikipedia.org/wiki/Eagle_S
- Nordic Warden: https://ukdefencejournal.org.uk/britain-launches-ai-system-to-monitor-russian-shadow-fleet/
- NKT: https://www.offshorewind.biz/2021/09/09/using-ais-monitoring-to-reduce-the-risk-of-subsea-cable-failures-caused-by-external-factors
- Vesper Marine: https://www.hydro-international.com/content/news/vesper-marine-guardian-solution-to-protect-submarine-cable-system-in-thailand
- Space Data: https://prtimes.jp/main/html/rd/p/000000185.000080352.html
- ICPC/ITU fault statistics: https://www.brusselstimes.com/1448914/fishing-not-spies-more-likely-to-be-behind-damage-to-underwater-cables-says-un
- Digitraffic: https://digitraffic.fi/en/marine-traffic

**Lights Out:**
- https://www.opennetzero.org/electricity-north-west/unplanned-outages1
- https://www.enwl.co.uk/future-energy/data-and-digitalisation/data-portal/

**Other ideas' evidence (Memory Lane, Proof of Kin, PFD reports and more):** see the Sources section of `research/00_prep_doc_export_16Oct.md`.
