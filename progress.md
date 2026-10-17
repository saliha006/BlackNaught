# Blacknaught: progress log and conflict board

**Every builder, every prompt:** run `git fetch` and read only the entries that are new since you last checked, with `git diff HEAD..origin/main -- progress.md`. Look for any open `⚠️ Conflicts` line that names you. If you find one, tell your user, then agree a fix with the person who flagged it before you touch that area.

**When you merge to `main`:** append one entry in this format, newest at the bottom:

```
### <YYYY-MM-DD HH:MM> — <feature> — @<builder>
- Shipped: <what changed, why>
- Touched: <files / modules / endpoints / shared contracts>
- ⚠️ Conflicts: @<Name> — <what of theirs this changes or could break> | none
- Conflict status: open | resolved by @<Name> <date>
```

## Latest
- **The volatile facts live here only:** current commit, test counts, what's merged vs local-only, and the VM status.
- **As of 2026-10-17 22:40:**
  - `main` holds the backend foundation (`backend/`, `db/`). 17 tests green on the VM (s390x), 97% coverage.
  - **VM:** reachable (s390x, z17 9175, NNPA flag present, Ubuntu 24.04.5, 3 vCPU / 7.8 GiB, 45 GB free). Docker 29.8 + Compose v5 installed; Jupyter (`notebook`) on :38888 with a custom token; IBM lab image pulled; backend stack `bn-backend` (postgres:17 + app) running.
  - All other docs stay local and are never pushed: the PRD, briefs, decisions and research.

---

### 2026-10-17 21:40 — repo scaffold — @sali
- Shipped: `.gitignore` keeps every doc local except `progress.md` and `README.md`. It also excludes data, models and secrets. Added this conflict board.
- Touched: `.gitignore`, `progress.md`
- ⚠️ Conflicts: @rama: the `Rama-Frontend` branch predates this `.gitignore`. Rebase on `main` before adding files, so docs and data don't get committed by accident.
- Conflict status: open

### 2026-10-17 21:50 — VM access for Sali — @sali
- Shipped: used the team key once to add Sali's own ed25519 public key to `linux1`'s `authorized_keys`; Sali now logs in with their own key (`ssh datathon`). Probe saved above. No other VM change.
- Touched: VM `~/.ssh/authorized_keys` (append only). Nothing removed.
- ⚠️ Conflicts: @ahmed: you own VM keys. Nothing of yours was changed, and the team key + your key are still there. Still yours: remove the leaked team key once everyone has their own, delete the Drive link, and change the portal password (it was in the form). Docker isn't installed yet; tell Sali if you want him to run HANDOFF §3.1.
- Conflict status: open

### 2026-10-17 22:15 — VM platform setup (Docker + Jupyter) — @sali
- Shipped: Docker CE 29.8 + Compose v5 on the VM (HANDOFF §3.1); `linux1` in the docker group. Jupyter container `notebook` on :38888 with a custom token (stored in `~/.secrets/jupyter_token`, mode 600; never in git or chat); iptables ACCEPT 38888, persisted via iptables-persistent. Pulled the IBM lab image (9.85 GB).
- Touched: VM packages, iptables, `~/shared`, `~/.secrets`
- ⚠️ Conflicts: @ahmed: this was your task 3, done so the team isn't blocked. Ask Sali for the token, or rotate it (`~/.secrets/jupyter_token`, then recreate `notebook`). Also: the lab image is **RHEL 10.2 with OpenSSL 3.5.5**, so ML-DSA and AES-GCM work inside `app` directly; a separate signer container may be unnecessary.
- Conflict status: open

### 2026-10-17 22:40 — backend foundation — @sali
- Shipped: pg8000 DB layer (one thread per connection, reconnect on dropped backends), migration runner with a drift guard, schema `bn` + roles (`bn_migrator`/`bn_ingest`/`bn_api`/`bn_agent`, API reads views only), append-only audit table, backend compose stack (`backend/compose.backend.yml`: postgres:17 + IBM lab image), `.gitattributes` forcing LF. 17 tests on s390x.
- Touched: `backend/`, `db/`, `.gitattributes`, `.gitignore`
- ⚠️ Conflicts: @ahmed: Postgres for the backend stack publishes only on 127.0.0.1:5432; your `/infra` compose should reuse `db/init` + `db/migrations` and the same secret names (`secrets/*`). @nate: the `prediction`/`triage_snapshot` tables assume the `predict()` shape in system-design-choices §7.
- Conflict status: open
