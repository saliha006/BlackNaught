#!/bin/bash
# Publish your edited shared docs to the `context` branch without switching branches.
# Usage: scripts/publish-context.sh "What changed, in plain words"
# Only files you changed since your last sync are sent. Everything else keeps the version already on `context`,
# so a stale local copy can never undo a teammate's edit. Refuses: a file changed on `context` AND locally,
# anything that looks like a credential, and, unless you are Sali, any shared doc other than your own brief.
# Who you are comes from `git config blacknaught.builder <sali|ahmed|nate|rama>` (set once per clone).
set -euo pipefail
# Git Bash on Windows rewrites "rev:.claude/..." arguments as Windows paths unless this is set
export MSYS_NO_PATHCONV=1
cd "$(git rev-parse --show-toplevel)"
msg=${1:?usage: scripts/publish-context.sh "what changed"}
gitdir=$(git rev-parse --git-dir)

builder=$(git config --get blacknaught.builder || true)
if [ -z "$builder" ]; then
  echo "publish refused: say who you are first: git config blacknaught.builder <sali|ahmed|nate|rama>" >&2
  exit 1
fi
synced=$(cat "$gitdir/context-synced" 2>/dev/null || true)
if [ -z "$synced" ]; then
  echo "publish refused: run scripts/sync-context.sh first" >&2
  exit 1
fi
git fetch -q origin context
parent=$(git rev-parse origin/context)

blob() { git rev-parse -q --verify "$1:$2" 2>/dev/null || echo none; }
candidates=$( { git ls-tree -r --name-only "$parent"
                printf '%s\n' CONTEXT-README.md CLAUDE.md BLACKNAUGHT.md DATATHON-CONTEXT.md \
                  builder-file-sali.md builder-file-ahmed.md builder-file-nate.md builder-file-rama.md \
                  "DATATHON INFO/research-and-codebase.md" "DATATHON INFO/IBMZ_Datathon_ClaudeCode_Handoff/HANDOFF.md"
                find .claude/skills -type f 2>/dev/null || true; } | sort -u)

changed=()
conflicts=()
while IFS= read -r f; do
  [ -f "$f" ] || continue
  mine=$(git hash-object "$f"); base=$(blob "$synced" "$f"); remote=$(blob "$parent" "$f")
  if [ "$mine" = "$base" ] || [ "$mine" = "$remote" ]; then continue; fi
  if [ "$remote" != "$base" ]; then conflicts+=("$f"); else changed+=("$f"); fi
done <<< "$candidates"

if [ ${#conflicts[@]} -gt 0 ]; then
  printf 'publish refused: changed on context since your last sync AND locally:\n' >&2
  printf '  %s\n' "${conflicts[@]}" >&2
  echo "run scripts/sync-context.sh (it saves your copy under .git/context-backup/), re-apply your edit, re-run" >&2
  exit 1
fi
if [ ${#changed[@]} -eq 0 ]; then
  echo "context: nothing to publish"
  exit 0
fi
if [ "$builder" != sali ]; then
  for f in "${changed[@]}"; do
    if [ "$f" != "builder-file-$builder.md" ]; then
      echo "publish refused: only Sali publishes $f; ask Sali (progress.md ping) or undo your local edit" >&2
      exit 1
    fi
  done
fi
if grep -l -E '23Tp&dUH|1Tr1oqA0kv8tt|BEGIN (OPENSSH|RSA) PRIVATE|Apikey [0-9a-f]{20}' "${changed[@]}" 2>/dev/null; then
  echo "publish refused: a file above looks like it contains a credential" >&2
  exit 1
fi

export GIT_INDEX_FILE="$gitdir/context-index"
rm -f "$GIT_INDEX_FILE"
git read-tree "$parent"
for f in "${changed[@]}"; do
  git update-index --add --cacheinfo "100644,$(git hash-object -w "$f"),$f"
done
tree=$(git write-tree)
rm -f "$GIT_INDEX_FILE"
unset GIT_INDEX_FILE
commit=$(git commit-tree "$tree" -p "$parent" -m "$msg")
git push -q origin "$commit:refs/heads/context"

# teammates' newer copies replace yours, so the stamp below matches the disk and the next publish sees only real edits
while IFS= read -r f; do
  latest=$(git rev-parse "$commit:$f")
  if [ ! -f "$f" ] || [ "$(git hash-object "$f")" != "$latest" ]; then
    mkdir -p "$(dirname "$f")"
    git cat-file blob "$latest" > "$f"
  fi
done < <(git diff --name-only --diff-filter=d "$synced" "$commit")
echo "$commit" > "$gitdir/context-synced"
echo "context: published ${commit:0:7} ($msg): ${changed[*]}"
