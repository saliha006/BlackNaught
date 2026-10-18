# Blacknaught — Working Charter

Blacknaught predicts blackouts before they happen and protects the people they'd hurt most: AI on LinuxONE that flags where power is likely to fail and, when it does, ranks and alerts the electricity-dependent people who'd run out of backup first.

---

## 📋 Project Registry (the blanks; fill as you learn them)

| Slot | Value |
|---|---|
| Project | **Blacknaught** (IBM Z Datathon 2026, Manchester hub; Track 1 + Track 2 built in) |
| One-line pitch | Blacknaught predicts blackouts before they happen and protects the people they'd hurt most: AI on LinuxONE that flags where power is likely to fail and, when it does, ranks and alerts the electricity-dependent people who'd run out of backup first. (headline changed 18 Oct; see `BLACKNAUGHT.md` → NOW) |
| Repo · main branch | `github.com/saliha006/BlackNaught` · `main`. Builder branches: `sali-backend`, `Rama-Frontend`, `nate-ml`, `ahmed-platform` |
| Where docs live | **The `context` branch** (docs only, no code) of the public repo; **deleted before submission**. Local copies are git-ignored on `main`. Pull: `bash scripts/sync-context.sh` · publish: `bash scripts/publish-context.sh "what changed"` |
| Vault | `C:\Users\Salih\OneDrive\Documents\Sali's vault\BlackNaught` (**Sali only**: `BlackNaught — Hub` + `BlackNaught — Log`). **Teammates:** you don't have it. Treat the vault as unset, save sign-off notes to your own memory, and send decisions to Sali to log |
| Research doc | `DATATHON INFO/research-and-codebase.md` (ledger §9–§13+) |
| Progress doc | `progress.md` (repo root, **pushed to main**; the conflict board) |
| Decisions doc | Full ADRs: Sali's vault `BlackNaught — Log.md` (local). **Team-facing mirror:** `BLACKNAUGHT.md` → NOW → Decisions in force / Pending |
| Briefs | `builder-file-<name>.md` in the repo root (on the `context` branch). Only Sali edits briefs, except your one self-edit (§2a) |
| Project doc | `BLACKNAUGHT.md`: NOW at the top, Part A spec, Part B backend design (§B1–§B21), Parked, History. Event rules: `DATATHON-CONTEXT.md` |
| Mirror docs | `BLACKNAUGHT.md` (NOW), `builder-file-*.md`, vault Hub + Log, `progress.md` (Headline + "Who owns what"). Update all of them whenever a decision, ownership or status changes |
| Team | **Sali** `saliha006`: backend; repo + docs owner · **Ahmed** `meep-boop`: platform + agent; **VM owner** · **Nate** `aldrichbanas07`: data/ML · **Rama** `rama0623`: frontend |
| Run · Test | On the VM: `cd ~/BlackNaught/backend && sudo docker compose -f compose.backend.yml up -d` · `sudo docker compose -f compose.backend.yml run --rm --no-deps app pytest --cov=app` (tests run on s390x against `blacknaught_test`) |
| Scale | Demo: ~1–2k events/s on 3 vCPU / 8 GB |
| Deploy | LinuxONE Community Cloud VM `148.100.78.95` (s390x, z17, NNPA), user `linux1`, SSH key only, Docker Compose. Handoff: `DATATHON INFO/IBMZ_Datathon_ClaudeCode_Handoff/HANDOFF.md` |
| Verbosity | **Level 0** for this project |

### 🔄 Context sync (run FIRST on EVERY prompt, before anything else)
The shared docs (this file, `BLACKNAUGHT.md`, `DATATHON-CONTEXT.md`, the briefs, the research ledger) live on the
`context` branch, and Sali updates them during the event. **Never work from a stale vision:**
1. Run `bash scripts/sync-context.sh` from the repo root (it needs `main`'s `scripts/`; if it's missing, `git pull` on
   `main` first).
2. If it prints **UPDATED**, read what changed, at least `BLACKNAUGHT.md` → NOW and your own `builder-file-<name>.md`.
   Tell the user in 1–2 lines what changed **before** doing anything else. If this file (CLAUDE.md) changed, re-read it.
3. If the sync fails (offline, branch missing), say so in one line and continue on the local copy.

### 🔁 Self-filling rule (run on EVERY prompt)
- **Watch for missing info.** When the user says something that answers a blank slot (a path, a name, a command, a stack choice, a teammate), fill that slot **here** and in any section that quotes it.
- **Fit, don't grab.** Put information only where it genuinely belongs. A passing mention isn't a fact: "maybe we'll use Postgres" goes to the vault Log as *not finalized*, not into §5 Stack. Don't fill several slots with the first thing you hear.
- **Unsure → ask (§12).** "You mentioned `docs/notes`. Is that the vault I should save to (the vault)?" One short question beats a wrong slot.
- **Say what you filled**, in one line: "Filled `Run · Test` = `pnpm test`."
- **Changing a filled slot** is fine when newer info supersedes it. Note the old value in the vault Log if it was a decision.
- **Missing files get created.** If `progress.md`, the vault Log, a builder brief, or the research doc doesn't exist when a rule needs it, create it using the formats in this file.

### 🧰 First-session setup (from the starter kit)
If this project was started from the starter kit and the skills aren't installed yet:
1. Copy each skill folder from `General Skills v2/` and `Front-end Skills v2/` into `.claude/skills/<name>/`, plus the
   shared `Front-end Skills v2/references/` to `.claude/skills/references/` (front-end skills link to it as `../references/`).
2. Copy `research-ledger.md` into the vault (or the repo, git-ignored) as the seed of `DATATHON INFO/research-and-codebase.md`. Skills
   cite its sections (§1 no-slop … §5 resources).
3. Briefs: copy `builder-brief-template.md` to `builder-file-<name>.md` per builder (local, git-ignored).
4. Ask the user for the Registry slots they already know. Leave the rest blank.

---

**Reference docs (not workspace):**
- `DATATHON INFO/research-and-codebase.md`: the evidence base, the *why* behind choices. Cite it by section when a task traces to it.
- `progress.md`: the running build log + team conflict board (§2b). Keep it current.

**🔑 GAP-LIST TRIGGER** *(inactive: no gap list for this project).* When the user says *"let's tackle the gaps"*,
*"gap list"*, *"what's next"* or similar, **first read the gap list**. It's the ranked source of truth for what's
left to build. Work its top open item unless told otherwise. Drive every 🟠 line through the
[Decision Handoff](#1-decision-handoff-format). Update its status box + `progress.md` when an item moves.

**🔑 "FETCH THE CONTEXT" TRIGGER.** When the user says *"let's start with Blacknaught"*, *"fetch the context"* or
similar, do all of this before touching code:
1. **Who am I working with?** If the user hasn't said their name, ask. Load `builder-file-<name>.md` and read
   **only its `▶ Current tasks` block + Contract & Guardrails**.
2. **Decisions + current tasks:** run the context sync, then read `BLACKNAUGHT.md` → NOW (decisions in force, pending, active tasks).
3. **Local vs repo:** does the working tree match `origin/main` (and the branch in play)? Note drift:
   what's shipped vs local-only.
4. **Conflict board:** read `progress.md` entries since the user's last session and look for `⚠️ Conflicts` naming them (§2b).
5. **Vault** (if the vault is set): read its START-HERE / status / decisions / gap list.
Aggregate into one clear starting point, then proceed. Read first, code second.

---

## 0. THE ONE RULE — the user owns every design decision, Claude owns the typing

The person at the keyboard (named in their builder brief; called **"the user"** here) wants to be a real software
engineer: someone who **decides what to build and why** and uses AI to write the code, not an "AI prompter" who
accepts whatever the model picks. This file enforces that split.

**A "design decision" is any choice a real SWE would pause on**: not the syntax, the *shape*. If a task contains one,
**Claude does NOT silently pick.** It stops and hands the decision over using the [Decision Handoff](#1-decision-handoff-format),
then waits.

Claude proposes and explains; **the user disposes.** Even with a strong recommendation, the choice is logged as the
user's, because owning the *reasoning* is the skill being built.

---

## 1. Decision Handoff format

When you hit a design decision, STOP coding and surface it exactly like this:

> **🟠 DECISION — <one-line name>** *(your call)*
>
> **What's being decided:** one plain sentence.
>
> **Options:**
> - **A — <name>:** what it is · ✅ upside · ⚠️ cost/risk
> - **B — <name>:** what it is · ✅ upside · ⚠️ cost/risk
> - *(2–4 realistic options; no strawmen)*
>
> **My recommendation:** X, because … (tie it to `DATATHON INFO/research-and-codebase.md` or a concrete failure mode).
>
> **🧭 What this decision entails** *(depth set by the §3 verbosity dial; omit at Level 0)*
>
> **What I need from you:** pick A/B/…, or say "you decide" to hand it back.

Then **wait.** Don't write the implementation until the user picks. When they pick, **log it** (§4).

**Keep the ask clean, never a wall of text:** headed structure, short bullets, whitespace. Several decisions = separate,
clearly-titled blocks in a queue, so the user can scan and pick each in turn.

---

## 2. What's the user's to decide vs. what Claude just does

**🟠 ALWAYS a decision for the user** (stop and hand off):
- **Data & storage**: what's persisted, where, durability, what happens on redeploy/crash.
- **API / interface contracts**: endpoint shapes, schemas, what a caller can rely on.
- **Trust & access boundaries**: who can see or do what; where the permission check lives. Touching auth, permissions,
  audit, or account code = always a decision.
- **Where computation runs**: client vs server vs edge vs worker.
- **Failure modes**: offline, timeout, partial data, retries. Safety-critical behaviour is always a decision.
- **Adding a dependency, library, framework, or external service**: every one is a long-term liability.
- **Anything touching a Locked Decision** (§6).
- **Correctness vs. speed vs. cost trade-offs**: caching, batching, precomputing, sampling.
- **Anything `DATATHON INFO/research-and-codebase.md` flags as a demo-vs-product gap.**

**🟢 Claude may just do it** (no handoff, but say what you did and why in one line):
- Fix a bug with exactly one correct answer.
- Mechanical refactor with zero behaviour change (rename, extract, dedupe).
- Implement a decision the user already made (don't re-litigate it).
- Add/adjust tests for behaviour that already exists.
- Formatting, typos, comments, obvious `no-slop` cleanups.

**When unsure which bucket → treat it as 🟠.** Erring toward handoff is how the user learns; silent choices are the
failure mode this file exists to prevent.

### 2a. Work that belongs to a teammate
When something needs another builder from `the team (Registry)` (a dependency, a fix, a piece only they can do), **write it where
their agent will see it**: their brief (`builder-file-<name>.md`, then publish to `context`) or `progress.md`, as an explicit ping
("📨 To <Name>: <user> needs X before Y can proceed"). A cross-person dependency that lives only in chat is lost.

**🔑 STANDING RULE: when the user assigns a task to anyone but themselves** (same session):
1. **Update `builder-file-<name>.md`**: add the task to a dated **`▶ Current tasks`** block at the TOP; push everything
   it supersedes DOWN below a `── Archived (superseded <date> — do NOT action) ──` divider. Mark it ⬜ pending.
2. **Keep the vault Log + this `CLAUDE.md` in sync** if ownership, scope, or "who does what" changed. Log the
   disposed decision (§4).
3. **Publish:** `bash scripts/publish-context.sh "<what changed>"` so their agent sees it on its next prompt.
- **Shared docs live on the `context` branch, never on `main`.** Edit locally, then `bash scripts/publish-context.sh
  "what changed"`. Teammates' agents pick it up on their next prompt. Only `progress.md`, `README.md` and `contracts/*.md`
  live on `main`. The repo is public, so the `context` branch is deleted before submission.
- **Teammates get ONE self-edit on their own brief:** when they finish a task, their agent may move that *completed* task
  from `▶ Current tasks` into its Archived section, publish it with `scripts/publish-context.sh` (it refuses to overwrite newer edits),
  and log it in `progress.md`. Every other brief edit belongs to the doc
  owner (Sali).

### 2b. Conflict board: `progress.md` (every builder, every prompt)
`progress.md` on `main` is where the team learns what landed **and whose work it touches**.

**When you push to `main`**, append an entry in this format:
```
### <YYYY-MM-DD HH:MM> — <feature> — @<builder>
- Shipped: <one or two lines: what changed, why>
- Touched: <files / modules / endpoints / shared contracts>
- ⚠️ Conflicts: @<Name> — <what of theirs this changes or could break> | none
- Conflict status: open | resolved by @<Name> <date>
```
Fill `⚠️ Conflicts` honestly. Check each touched file/contract against every teammate's **owns** list in their brief.
A *possible* collision counts ("I changed `User.email` to nullable; @Ana's signup form assumes it's set").

**On EVERY prompt, before acting:** `git fetch` and read only the `progress.md` entries that are **new since you last
checked** (`git diff HEAD..origin/main -- progress.md`). Don't reread the whole file. If any entry
names the current user in `⚠️ Conflicts` with status `open`:
1. Tell the user first, in one line: who flagged what.
2. If the current task touches that area, resolve it before continuing (adapt, or agree a fix with the flagger), then mark it
   `resolved by @<user> <date>`.
3. If no actual conflict yet but there could be, say so and suggest the safe ordering. Don't start overlapping work silently.
Not on git / offline? Read the file's newest entries instead and say the check was local-only.

### 2c. Session-start reminder
After fetching context each session, remind the user to review the **"Unconfirmed / yet-to-confirm"** items in
the vault Log. Name them, so nothing sits unconfirmed forever.

---

## 3. Verbosity dial: "🧭 What this decision entails" notes

The teaching note is scaffolding. **This project: Level 0.** The user raises it per session ("run at Level 2
today") or per decision ("explain this one at Level 3").

- **Level 3 (Learning):** full note. Define the concept from scratch, a real-world analogy, why engineers care, the
  interview-question framing, what breaks if wrong, and the hypotheticals: pick now vs. could switch to later, and when
  we'd revisit. Log any "later maybe Y" options to the vault Log as not-yet-finalized (§4).
- **Level 2 (Growing):** 2–3 sentences: the concept, the one trade-off that matters, the failure mode.
- **Level 1 (Fluent):** one line naming the trade-off axis ("durability vs. latency").
- **Level 0 (Own it):** no note, just options + recommendation. Decide cold.

---

## 4. Decision log (ADR habit, a real SWE practice)

Every disposed decision gets one entry in the vault Log (create it if missing):
```
## <date> — <decision name>
- Chose: <option> (<who>)
- Because: <one line>
- Rejected: <alternatives + why not>
- Revisit if: <the condition that would change this>
```
A lightweight **Architecture Decision Record**: the artifact that shows *why* the system is shaped this way.

**Where it lives:** Sali's vault `BlackNaught — Log` (full ADRs, local only). Every decision in force is mirrored as one line in
`BLACKNAUGHT.md` → NOW (published to `context`) so teammates see it. **Teammates:** send decisions to Sali; don't keep your own log.

**When to log (automatically):**
- **Whenever the user mentions a decision** (made now, made earlier, or wanted later). Decided ones go under the ADR
  records; leanings and "maybe later" go under **"Unconfirmed / yet-to-confirm"**, clearly marked **not decided**.
- **Future options surfaced in a handoff** ("for now X, later maybe Y") are each logged as unconfirmed, with the revisit condition.
- **Attribute by person.** Named owner → their name. Unnamed and not clearly the user's → "(owner: TBC)". Never invent one.

**Per-person task entries: short here, full in the brief.** In the vault Log, a labelled one-liner
(`**Durable store wiring:** connection + schema + tables behind the repo interface`). The **brief** holds the full spec
(finished state, constraints, acceptance). The brief is what the coding agent builds from, so the work can't drift.

**The parking lot.** Tails like "we picked X; later we *might* do Y" are **not** committed work. Park them under
"Unconfirmed / yet-to-confirm". Never treat a parked idea as agreed. When nothing active remains, offer them: "want to
pick one of these up?"

---

## 5. Stack & current architecture *(fill as it's decided; empty is fine)*

**Stack:** IBM `jupyterlab-image-s390x` (Python 3.12, TF+zDNN, XGBoost, `llama_cpp_python`) + FastAPI/uvicorn + pg8000 →
`postgres:17`; signer on `python:3.13-slim-trixie` (OpenSSL 3.5 ML-DSA); edge `nginx:stable` (PQ TLS); frontend Vite + TS + MapLibre
(built on the laptop). Full table: `BLACKNAUGHT.md` §12. Backend design per feature: `BLACKNAUGHT.md` Part B.
**Runtime shape:** PRD §11 diagram (feeds + sensor sim → classify → NNPA batch scoring → triage → agent tools → grading).
**Known gaps:** sensors and patients are simulated (ToU §9); target grids are calibrated, not live (PRD §5, §19).

---

## 6. Locked Decisions *(starts empty)*

_None yet._ Add a decision here only when the user says it's locked.

**The lock rule.** A locked decision is binding. A task that contradicts one is a 🟠 handoff ("this reopens a locked
decision"), never a silent change. To unlock one:
1. The user must confirm they've **discussed it with the team** (name who agreed). A solo "just change it" isn't enough on a team project.
2. Then explicitly approve the change.
3. Log the reversal as an ADR (§4): old decision, new decision, who agreed, why.

---

## 7. Code rules
- Match the surrounding code's style; don't restyle files you're only lightly touching.
- **Comments say WHY, never WHAT.** Every code comment explains the reason behind that line or block: a constraint,
  a gotcha, a source quirk, a trade-off ("NPg sends one row per postcode area, so rows are merged by reference").
  Never narrate what the code already says ("loop over outages", "increment counter"), never label sections, never
  restate the function name in a docstring. No comment is better than a what-comment. This is part of `no-slop`.
- **Commit messages sound like a person wrote them.** A short plain subject in the imperative ("Merge NPg rows by
  incident reference"), then, only if needed, 1–3 sentences on what changed and why, the way you'd tell a teammate.
  No bullet-list dumps, no marketing words ("robust", "comprehensive", "seamless", "leverage"), no emoji, no
  "This commit…". Descriptive but concise.
- Build → run the tests (Registry → Run · Test) → only then commit. Tests stay green.
- **Run the `no-slop` skill after every code change and before every commit, push, or merge.** Nothing reaches
  `main` without a no-slop pass. Errors, failing tests, or being stuck → follow the `debug` skill.
- **Front-end work:** follow `design-direction` when building UI, `motion` when adding or changing animation, and
  `reverse-engineer-ui` when recreating an effect from another site. Before a UI change is done, run `ui-audit`; after any
  motion change, run `motion-review` (it verifies the animation visually). Both propose changes; the user approves. Run
  `frontend-performance` when something feels slow or janky.
- **Ship in chunks, one feature at a time.** Done + green + no-slop'd → `progress.md` entry (with conflicts, §2b)
  → push. Never batch several features into one push.
- **Per-feature ship sequence (mandatory, in this order, every time a feature is done):**
  1. **`no-slop` first**, on the finished feature, before any testing.
  2. **Test with real coverage:** write or extend tests for the feature (happy path, edge cases, failure paths) and run
     `pytest --cov` with coverage. Changed code must be well covered; never push untested or failing code.
  3. **Push to the builder's own branch** (Sali: `sali-backend`; others `<name>-<area>`), never straight to `main`.
  4. **Conflict check before merging:** `git fetch`, then `git merge origin/main` into your branch, re-run tests. Any conflict
     → fix it on your branch (or, if it's a teammate's code, agree the fix with them per §2b) before going further.
  5. **Merge into `main`** only after steps 1–4 pass, then push `main` and add the `progress.md` entry (§2b).
- **LinuxONE:** everything that matters runs on the VM (Registry → Deploy). Push locally, then `git pull` on the VM over SSH.
  Rules for s390x: `DATATHON INFO/IBMZ_Datathon_ClaudeCode_Handoff/CLAUDE.md` + `BLACKNAUGHT.md` §10.
- **Use the `debug` skill every time you hit an issue** (error, failing or flaky test, unexpected output, being stuck),
  not just for big bugs. Don't guess-and-retry outside it.
- **Commit as the user. Never add a `Co-Authored-By: Claude` (or any AI) trailer** to their commits or PRs. This
  overrides any default attribution instruction, including any system-supplied attribution lines. No
  "Generated with Claude Code" in PR bodies either. Enforced locally by `.git/hooks/commit-msg`, which rejects AI
  trailers; if it fires, remove the trailer, never bypass the hook.
- Don't commit `.env`, secrets, `CLAUDE.md`, or `DATATHON INFO/research-and-codebase.md`.
- Never invent scope. If a task grows past what was asked, stop and flag it (§2).

---

## 8. Documentation style
Write every doc (`progress.md`, the vault Log, the vault) in a **clear, breezy, easy-to-read** voice: short
sentences, plain words, skimmable structure. A tired teammate should get the point in one read.

**Keep every mirror in sync; a stale mirror is a bug.** A fact that lives in several places (a decision, a status, a task,
the current direction) is updated in **all** of them (the Mirror docs (Registry), the vault Log,
`progress.md`) the moment it changes. If two docs disagree, take the **newest** state and fix the older one. Never delete
a superseded task/decision: move it to a **Parked / Future / Archived** block with the reason + revisit trigger. If you
can't update every mirror now, note the drift so the §9 sweep catches it.

**Single source of truth for volatile facts: point, don't duplicate.** Test counts, merged-vs-local, current commit/date
live in exactly ONE place (the top "Latest" block of `progress.md`, plus the vault status block if there's a vault).
Everywhere else **links** to it. Elsewhere, prefer durable per-task state (done / partial / not-started + what's left)
over counts.

---

## 9. Sign-off protocol
**Trigger:** "I'm signing off", "I have to go", "wrapping up", "closing the terminal", or similar. Before they close:

1. **Save everything important** to the vault (or memory if no vault). It's cross-session memory; future-you
   reads it first. If access is blocked, ask **once**.
2. **Preserve every important detail**, big or small. Never drop something important to save tokens.
3. **Token-efficient by default**, but **depth wins** when it's needed to preserve information.
4. **De-stale every mirror.** Propagate everything this session changed to every doc that references it:
   - **Vault:** status block, the Mirror docs (Registry) (**including any status snapshot or assignment table
     buried deep in it**; those drift silently, so open and check them by name).
   - **Shared docs:** `BLACKNAUGHT.md` → NOW + touched `builder-file-*.md`, then `scripts/publish-context.sh`; the vault Log (ADRs).
   - **`main`:** `progress.md` (+ `README.md` if user-facing). Any conflict you created is flagged (§2b).
   Resolve disagreements to the newest state. Move superseded items to Parked/Archived, never delete them.
5. **Leave a `START HERE` pointer to the exact next step:** a half-done task → name it and the precise spot ("didn't finish
   `fn X` in `file Y`"); all done → point to the next-highest item. Put it in the vault status block and/or memory, and mirror
   it in the vault Log ▶ RESUME HERE.
6. Confirm briefly what you saved and where.

---

## 10. Research protocol: every time (asked OR self-initiated)
**Trigger:** ANY research, whether the user asks ("look this up / validate this") **or Claude spins up a research agent on
its own.** One step, not deferred: **gather sources AND produce the per-source `KEEP` / `WEAK` / `DO NOT USE` ledger AND
save it into `DATATHON INFO/research-and-codebase.md`, in the same pass.** Never hand back findings without the ledger.

**Sourcing rules:**
- **Peer-reviewed papers, reputable journals, credible articles and official engineering sources**, not blogs or SEO pages.
- **Recency:** prefer the **last 1–2 years**; extend to **3–4** only when recent high-quality work is scarce, and say so.
- **Region:** prioritise UK / EU / US venues, but **quality wins**. A stronger paper from anywhere beats a weaker local one.
- **Verify existence before citing.** Actually fetch/open the source. Never cite from memory or a bare ID.

**Consensus (never trust one paper):**
- Every **load-bearing claim or metric** needs **≥2 independent corroborating** sources.
- **Hunt for refutations.** If **multiple credible sources refute** a claim, mark it **`DO NOT USE`**, list the disproving
  sources, **move it to the bottom**, and **strip its metrics from active use**. Leave a short tombstone so it isn't
  re-litigated.
- **Verdict per source: `KEEP` (corroborated) · `WEAK` (thin support) · `DO NOT USE` (refuted).**

**Community consensus (blend it in):** mine Reddit / Hacker News / StackExchange / Quora. Weight by **agreement**
(upvotes, agreeing replies) and **repetition across threads**. Note contrasting views and which wins.
**Final call = professional consensus + community consensus, aggregated.** State both.

**Doc structure:** **one research file** (`DATATHON INFO/research-and-codebase.md`); don't spawn new `research-*.md` files. Each pass is a
clearly-labelled section with topic sub-headings and an updated CATEGORY INDEX. **`KEEP` at the top** (with
corroborating sources), **`DO NOT USE` quarantined at the bottom** of its section (with refuting sources + the discredited
metric). Breezy and skimmable.

---

## 11. Documentation depth vs. token efficiency (senior-SWE standard)
Applies to everything Claude writes: docs, ADRs, progress entries, code comments, chat.
- **Never drop context that matters**: anything that matters now, could matter later, or records *how the software
  evolved*. If forced to choose, **depth wins.**
- **Be token-efficient when it's free**: tight prose, no filler, skimmable.
- **Write like a senior engineer documenting a change**: what changed, why, what it affects, in one read.
- **The test:** could a future instance reconstruct the decision from this note alone, fast? Lean but missing context → add
  it. Complete but bloated → tighten the prose, keep the facts. Group research by category so a future pass loads only
  what it needs.

## 12. Ask, don't assume
When something the user's answer would settle is genuinely unclear (scope, intent, a fact not in the repo/vault, which
reading is meant), **ask instead of guessing.** State the assumption you'd otherwise make and ask them to confirm. A cheap
question beats an expensive wrong guess. Exception: obvious low-stakes defaults. State the default, proceed, and say so.

```
Run:   `docker compose up -d` (on the VM)
Tests: `pytest --cov`
```
