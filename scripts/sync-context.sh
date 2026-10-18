#!/bin/bash
# Pull the latest shared docs (CLAUDE.md, BLACKNAUGHT.md, briefs, research...) from the `context` branch into this
# folder. Files are unpacked, never staged: main's .gitignore ignores them, so they can't be committed by accident.
# Prints what changed since the last sync so Claude can tell the user before working.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git fetch -q origin context
new=$(git rev-parse origin/context)
stamp="$(git rev-parse --git-dir)/context-synced"
old=$(cat "$stamp" 2>/dev/null || echo none)
if [ "$new" = "$old" ]; then
  echo "context: up to date (${new:0:7})"
  exit 0
fi
git archive --format=tar origin/context | tar -xf -
echo "$new" > "$stamp"
if [ "$old" = none ]; then
  echo "context: first sync at ${new:0:7}. Read BLACKNAUGHT.md (NOW) and your builder-file-<name>.md."
else
  echo "context: UPDATED ${old:0:7} -> ${new:0:7}"
  git log --format='  %h %s (%an, %ar)' "$old..$new"
  git diff --stat "$old" "$new" | tail -n +1
fi
