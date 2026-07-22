#!/usr/bin/env bash
# Commit + push a pending plugin.json change across every per-plugin repo.
#
# Each plugin directory here is its OWN git repo (see .gitignore: `*/`), pointing
# at github.com/DJTouchette/workspacer-plugin-<dir>. When you change a plugin's
# manifest (e.g. bump its `version`), this stages just plugin.json, commits it
# with a shared message, and — with --push — pushes each repo to its origin.
#
# Safe by default: DRY RUN unless you pass --push. It only ever touches
# plugin.json, skips repos with no plugin.json change, refuses a repo that has
# OTHER unstaged changes (so you don't sweep unrelated work into the commit),
# and never creates branches — it commits on whatever branch is checked out.
#
# Usage:
#   ./sync-plugin-manifests.sh                       # dry run, default message
#   ./sync-plugin-manifests.sh --push                # commit + push
#   ./sync-plugin-manifests.sh --push -m "message"   # custom commit message
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUSH=0
MSG="Add version field for update detection"

while [ $# -gt 0 ]; do
  case "$1" in
    --push) PUSH=1; shift ;;
    -m|--message) MSG="${2:?-m needs a message}"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ "$PUSH" -eq 1 ] && MODE="PUSH" || MODE="DRY RUN"
echo "== sync-plugin-manifests ($MODE) =="
echo "   message: $MSG"
echo

committed=0 pushed=0 skipped=0 blocked=0
for dir in "$ROOT"/*/; do
  d="$(basename "$dir")"
  [ -d "$dir/.git" ] || continue
  git -C "$dir" ls-files --error-unmatch plugin.json >/dev/null 2>&1 || continue

  # Nothing staged/unstaged for plugin.json → already in sync, skip quietly.
  if git -C "$dir" diff --quiet -- plugin.json && \
     git -C "$dir" diff --cached --quiet -- plugin.json; then
    skipped=$((skipped+1))
    continue
  fi

  # Refuse if anything OTHER than plugin.json is dirty — don't sweep it up.
  other="$(git -C "$dir" status --porcelain | grep -v ' plugin.json$' || true)"
  if [ -n "$other" ]; then
    echo "!! $d: other uncommitted changes present — skipping"
    echo "$other" | sed 's/^/     /'
    blocked=$((blocked+1))
    continue
  fi

  branch="$(git -C "$dir" rev-parse --abbrev-ref HEAD)"
  ver="$(python3 -c "import json;print(json.load(open('$dir/plugin.json')).get('version',''))" 2>/dev/null)"
  echo ">> $d (branch $branch, version ${ver:-none})"

  if [ "$PUSH" -eq 0 ]; then
    git -C "$dir" --no-pager diff -- plugin.json | sed 's/^/     /'
    continue
  fi

  git -C "$dir" add plugin.json
  if git -C "$dir" commit -q -m "$MSG"; then
    committed=$((committed+1))
    if git -C "$dir" push -q origin "$branch"; then
      echo "   pushed to origin/$branch"
      pushed=$((pushed+1))
    else
      echo "!! $d: push failed" >&2
    fi
  else
    echo "!! $d: commit failed" >&2
  fi
done

echo
echo "== done: committed=$committed pushed=$pushed skipped(in-sync)=$skipped blocked=$blocked =="
[ "$PUSH" -eq 0 ] && echo "   (dry run — re-run with --push to commit + push)"
