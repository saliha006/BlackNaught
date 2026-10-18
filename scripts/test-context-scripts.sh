#!/bin/bash
# Runs sync-context.sh and publish-context.sh against a throwaway remote: a stale copy must never undo a teammate's
# published edit, teammates may publish only their own brief, and sync must never lose an unpublished local edit.
# Usage: bash scripts/test-context-scripts.sh
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
quiet() { "$@" >/dev/null 2>&1; }
# MSYS_NO_PATHCONV only around `git show`: elsewhere Git Bash must still translate the /tmp paths for Windows git
on_context() { (cd "$tmp/$1" && git fetch -q origin context && MSYS_NO_PATHCONV=1 git show "origin/context:$2"); }

git init -q --bare "$tmp/remote.git"
git init -q "$tmp/seed"
cd "$tmp/seed"
git config user.email seed@test
git config user.name seed
git checkout -q -b main
mkdir scripts
cp "$here/sync-context.sh" "$here/publish-context.sh" scripts/
printf '* text=auto eol=lf\n' > .gitattributes
printf '*.md\n.claude/\n' > .gitignore
git add .
git commit -qm main
git remote add origin "$tmp/remote.git"
git push -q origin main
git checkout -q --orphan context
git rm -rq --cached .
rm -rf scripts .gitignore
mkdir -p "DATATHON INFO/IBMZ_Datathon_ClaudeCode_Handoff" .claude/skills/demo
for f in CONTEXT-README.md CLAUDE.md BLACKNAUGHT.md DATATHON-CONTEXT.md builder-file-sali.md builder-file-ahmed.md \
         builder-file-nate.md builder-file-rama.md "DATATHON INFO/research-and-codebase.md" \
         "DATATHON INFO/IBMZ_Datathon_ClaudeCode_Handoff/HANDOFF.md" .claude/skills/demo/SKILL.md; do
  echo "$f v1" > "$f"
done
git add -f .
git commit -qm docs
git push -q origin context

for who in sali nate ahmed; do
  git clone -q -b main "$tmp/remote.git" "$tmp/$who"
  git -C "$tmp/$who" config user.email "$who@test"
  git -C "$tmp/$who" config user.name "$who"
  git -C "$tmp/$who" config blacknaught.builder "$who"
  (cd "$tmp/$who" && quiet bash scripts/sync-context.sh)
done

# tonight's bug: Ahmed publishes his own brief from a sync older than Nate's publish
cd "$tmp/nate"
echo "nate: task 3 done" >> builder-file-nate.md
quiet bash scripts/publish-context.sh "nate done" || fail "nate could not publish his own brief"
cd "$tmp/ahmed"
echo "ahmed: task 6 done" >> builder-file-ahmed.md
quiet bash scripts/publish-context.sh "ahmed done" || fail "ahmed could not publish his own brief"
on_context ahmed builder-file-nate.md | grep -q "task 3 done" || fail "ahmed's stale copy undid nate's edit"
grep -q "task 3 done" "$tmp/ahmed/builder-file-nate.md" || fail "publish left ahmed's stale copy in place"

# a skill added on context after Nate's last sync survives Nate's next publish
cd "$tmp/sali"
quiet bash scripts/sync-context.sh
mkdir -p .claude/skills/added
echo "new skill" > .claude/skills/added/SKILL.md
quiet bash scripts/publish-context.sh "sali adds a skill" || fail "sali could not add a skill"
cd "$tmp/nate"
echo "nate: task 4 done" >> builder-file-nate.md
quiet bash scripts/publish-context.sh "nate again" || fail "nate's second publish failed"
on_context nate .claude/skills/added/SKILL.md | grep -q "new skill" || fail "nate's publish dropped a skill added after his sync"

# teammates can't publish someone else's brief or other shared docs; Sali can publish several
cd "$tmp/ahmed"
quiet bash scripts/sync-context.sh
echo "ahmed edits nate" >> builder-file-nate.md
quiet bash scripts/publish-context.sh "x" && fail "ahmed published nate's brief"
on_context ahmed builder-file-nate.md > builder-file-nate.md
echo "ahmed edits the rules" >> CLAUDE.md
quiet bash scripts/publish-context.sh "x" && fail "ahmed published CLAUDE.md"
on_context ahmed CLAUDE.md > CLAUDE.md
cd "$tmp/sali"
quiet bash scripts/sync-context.sh
echo "sali tidies" >> builder-file-nate.md
echo "sali tidies" >> builder-file-ahmed.md
quiet bash scripts/publish-context.sh "sali tidies two briefs" || fail "sali could not publish two briefs"

# publishing without saying who you are is refused
cd "$tmp/ahmed"
git config --unset blacknaught.builder
quiet bash scripts/sync-context.sh
echo "x" >> builder-file-ahmed.md
quiet bash scripts/publish-context.sh "x" && fail "publish ran without blacknaught.builder"
git config blacknaught.builder ahmed
on_context ahmed builder-file-ahmed.md > builder-file-ahmed.md

# Nate's last sync predates Sali's tidy of his brief: publishing is refused, and sync keeps his edit as a backup
cd "$tmp/nate"
echo "nate: unpublished note" >> builder-file-nate.md
quiet bash scripts/publish-context.sh "conflict" && fail "publish ignored a change made on both sides"
quiet bash scripts/sync-context.sh
grep -rq "unpublished note" .git/context-backup || fail "sync lost nate's unpublished edit"
grep -q "sali tidies" builder-file-nate.md || fail "sync didn't bring in sali's tidy"

echo "PASS: context scripts"
