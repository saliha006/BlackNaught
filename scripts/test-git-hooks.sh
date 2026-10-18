#!/bin/bash
# Runs real commits through scripts/git-hooks in a throwaway repo, the way git runs the hooks for you.
# Usage: bash scripts/test-git-hooks.sh   (gitleaks must be on PATH for the secret check)
set -u
hooks=$(cd "$(dirname "$0")/git-hooks" && pwd)
repo=$(mktemp -d)
trap 'rm -rf "$repo"' EXIT
cd "$repo" || exit 1
git init -q && git config user.name test && git config user.email test@example.invalid && git config core.hooksPath "$hooks"
git config core.autocrlf false  # the result mustn't depend on this machine's line-ending setting
failed=0

expect() {  # expect <what> <wanted exit code> <command...>
  local what=$1 want=$2
  shift 2
  "$@" >/dev/null 2>&1
  local got=$?
  if [ "$got" = "$want" ]; then echo "PASS  $what"; else echo "FAIL  $what (exit $got, wanted $want)"; failed=1; fi
}

echo ok > notes.txt && git add notes.txt
expect "a clean commit goes through" 0 git commit -q -m "Add notes"

# Built at run time, so this script never holds a token-shaped string for gitleaks to flag in our own repo.
printf 'token = "ghp_%s"\n' "$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 36)" > config.txt && git add config.txt
expect "a staged GitHub token is blocked" 1 git commit -q -m "Add config"
git rm -q --cached config.txt && rm config.txt

echo more >> notes.txt && git add notes.txt
expect "an AI co-author trailer is refused" 1 git commit -q -m "Tweak notes" -m "Co-Authored-By: Claude <noreply@anthropic.com>"

no_gitleaks=$(printf '%s' "$PATH" | tr ':' '\n' | while IFS= read -r dir; do
  [ -e "$dir/gitleaks" ] || [ -e "$dir/gitleaks.exe" ] || printf '%s:' "$dir"
done)
expect "without gitleaks the commit still goes through" 0 env PATH="$no_gitleaks" git commit -q -m "Tweak notes"
exit $failed
