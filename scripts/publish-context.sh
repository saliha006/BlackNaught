#!/bin/bash
# Publish the local shared docs to the `context` branch without switching branches.
# Usage: scripts/publish-context.sh "What changed, in plain words"
# Refuses to overwrite a file someone else changed on `context` since your last sync (sync, merge, re-run),
# and refuses anything that looks like a credential.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
msg=${1:?usage: scripts/publish-context.sh "what changed"}
gitdir=$(git rev-parse --git-dir)
FILES=(CONTEXT-README.md CLAUDE.md BLACKNAUGHT.md DATATHON-CONTEXT.md
       builder-file-sali.md builder-file-ahmed.md builder-file-nate.md builder-file-rama.md
       "DATATHON INFO/research-and-codebase.md" "DATATHON INFO/IBMZ_Datathon_ClaudeCode_Handoff/HANDOFF.md")
while IFS= read -r f; do FILES+=("$f"); done < <(find .claude/skills -type f | sort)

if grep -l -E '23Tp&dUH|1Tr1oqA0kv8tt|BEGIN (OPENSSH|RSA) PRIVATE|Apikey [0-9a-f]{20}' "${FILES[@]}" 2>/dev/null; then
  echo "publish refused: a file above looks like it contains a credential" >&2
  exit 1
fi

parent=""
if git fetch -q origin context 2>/dev/null; then parent=$(git rev-parse origin/context); fi
synced=$(cat "$gitdir/context-synced" 2>/dev/null || echo "")

blob() { git rev-parse -q --verify "$1:$2" 2>/dev/null || echo none; }
if [ -n "$parent" ] && [ -n "$synced" ] && [ "$parent" != "$synced" ]; then
  conflicts=()
  for f in "${FILES[@]}"; do
    base=$(blob "$synced" "$f"); remote=$(blob "$parent" "$f"); mine=$(git hash-object "$f")
    if [ "$remote" != "$base" ] && [ "$mine" != "$base" ] && [ "$mine" != "$remote" ]; then conflicts+=("$f"); fi
  done
  if [ ${#conflicts[@]} -gt 0 ]; then
    printf 'publish refused: changed on context since your last sync AND locally:\n' >&2
    printf '  %s\n' "${conflicts[@]}" >&2
    echo "merge by hand (git show origin/context:<file>), then re-run" >&2
    exit 1
  fi
fi

export GIT_INDEX_FILE="$gitdir/context-index"
rm -f "$GIT_INDEX_FILE"
for f in "${FILES[@]}"; do
  git update-index --add --cacheinfo "100644,$(git hash-object -w "$f"),$f"
done
tree=$(git write-tree)
rm -f "$GIT_INDEX_FILE"
unset GIT_INDEX_FILE

if [ -n "$parent" ] && [ "$tree" = "$(git rev-parse "$parent^{tree}")" ]; then
  echo "context: nothing changed"
  exit 0
fi
commit=$(git commit-tree "$tree" ${parent:+-p "$parent"} -m "$msg")
git push -q origin "$commit:refs/heads/context"
echo "$commit" > "$gitdir/context-synced"
echo "context: published ${commit:0:7} ($msg)"
