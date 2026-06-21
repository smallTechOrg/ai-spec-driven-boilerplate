#!/usr/bin/env bash
# Zer0 hook — enforce non-negotiable #5: every commit is pushed immediately.
# Runs after each Bash tool call (PostToolUse). If the current branch has commits
# that aren't on its upstream, push them. Best-effort and silent on success.
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$root" || exit 0

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" || exit 0
[ "$branch" = "HEAD" ] && exit 0   # detached; nothing to do

upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"

if [ -z "$upstream" ]; then
  # No upstream yet — publish the branch.
  if git push -u origin "$branch" >/dev/null 2>&1; then
    exit 0
  fi
  echo "Zer0 hook: could not publish '$branch' — push manually." >&2
  exit 0
fi

ahead="$(git rev-list --count '@{u}..HEAD' 2>/dev/null || echo 0)"
if [ "${ahead:-0}" -gt 0 ]; then
  if ! git push >/dev/null 2>&1; then
    echo "Zer0 hook: git push failed ($ahead commit(s) unpushed) — push manually." >&2
  fi
fi
exit 0
