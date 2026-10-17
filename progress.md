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
- **As of 2026-10-17 23:25:**
  - `main` holds `README.md`, `.gitignore` and this file. No code yet.
  - **VM:** reachable (s390x, z17 9175, NNPA flag present, Ubuntu 24.04.5, 3 vCPU / 7.8 GiB, 45 GB free). **Docker is not installed yet.**
  - All other docs stay local and are never pushed: the PRD, briefs, decisions and research.

---

### 2026-10-17 21:40 — repo scaffold — @sali
- Shipped: `.gitignore` keeps every doc local except `progress.md` and `README.md`. It also excludes data, models and secrets. Added this conflict board.
- Touched: `.gitignore`, `progress.md`
- ⚠️ Conflicts: @rama: the `Rama-Frontend` branch predates this `.gitignore`. Rebase on `main` before adding files, so docs and data don't get committed by accident.
- Conflict status: open

### 2026-10-17 23:25 — VM access for Sali — @sali
- Shipped: used the team key once to add Sali's own ed25519 public key to `linux1`'s `authorized_keys`; Sali now logs in with their own key (`ssh datathon`). Probe saved above. No other VM change.
- Touched: VM `~/.ssh/authorized_keys` (append only). Nothing removed.
- ⚠️ Conflicts: @ahmed: you own VM keys. Nothing of yours was changed, and the team key + your key are still there. Still yours: remove the leaked team key once everyone has their own, delete the Drive link, and change the portal password (it was in the form). Docker isn't installed yet; tell Sali if you want him to run HANDOFF §3.1.
- Conflict status: open
