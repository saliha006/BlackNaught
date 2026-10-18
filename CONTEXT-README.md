# Blacknaught: shared context (the `context` branch)

This branch holds **only the team's shared docs**, no code. Code lives on `main`. ⚠ The repo is public, so **this branch is deleted before submission**.

| File | What |
|---|---|
| `CLAUDE.md` | Our working rules. Your Claude Code reads it automatically, and it syncs this branch at the start of every prompt |
| `BLACKNAUGHT.md` | **The project doc:** NOW (current decisions + active tasks) at the top, then the spec (Part A), backend design (Part B), Parked, History |
| `DATATHON-CONTEXT.md` | Event rules, judging, what wins, why Blacknaught |
| `builder-file-<name>.md` | Each person's task list (read your own) |
| `DATATHON INFO/research-and-codebase.md` | The evidence ledger (KEEP / WEAK / DO NOT USE) |
| `DATATHON INFO/IBMZ_Datathon_ClaudeCode_Handoff/HANDOFF.md` | IBM platform facts (authoritative) |
| `.claude/skills/` | `no-slop`, `debug` + the frontend skills |

**How the sync works:**
- In your clone of `main`, run `bash scripts/sync-context.sh`. It unpacks these files into your folder, never staged, so they can't be committed to `main`. It prints what changed.
- After the first sync, CLAUDE.md makes your Claude run it at every prompt.
- **Only Sali publishes**, except your one self-edit: moving your own finished task to Archived. Publish with `bash scripts/publish-context.sh "what changed"`. It refuses to overwrite someone else's newer edit and refuses anything that looks like a credential.
