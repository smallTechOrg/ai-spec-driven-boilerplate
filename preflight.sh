#!/usr/bin/env bash
# Run this before a demo or workshop: catches missing tools and config in ~5 seconds.
set -euo pipefail

OK="\033[32m✓\033[0m"
FAIL="\033[31m✗\033[0m"
WARN="\033[33m!\033[0m"
errors=0

check() {
  local label="$1"; local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    printf "$OK $label\n"
  else
    printf "$FAIL $label\n"
    errors=$((errors+1))
  fi
}

warn() {
  local label="$1"; local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    printf "$OK $label\n"
  else
    printf "$WARN $label (optional — some features won't work)\n"
  fi
}

echo ""
echo "=== BlogForge / Agent Boilerplate — Pre-flight Check ==="
echo ""

# Tools
check "git installed"          "git --version"
check "python 3.12+"           "python3 -c 'import sys; assert sys.version_info >= (3,12)'"
check "uv installed"           "uv --version"
check "claude CLI installed"   "claude --version"

echo ""

# Repo state
check "inside a git repo"      "git rev-parse --git-dir"
check ".env file exists"       "test -f .env"
check "GEMINI_API_KEY set"     "grep -q 'GEMINI_API_KEY=.' .env 2>/dev/null"
warn  "TAVILY_API_KEY set"     "grep -q 'TAVILY_API_KEY=.' .env 2>/dev/null"

echo ""

# Python env
if [ -d ".venv" ]; then
  check ".venv exists"         "test -d .venv"
  check "key packages present" ".venv/bin/python -c 'import langgraph, fastapi, sqlalchemy'"
else
  printf "$WARN .venv not found — run: uv sync\n"
  errors=$((errors+1))
fi

echo ""

# Data dirs
[ -d "data" ] || mkdir -p data && printf "$OK data/ directory ready\n"
[ -d "images" ] || mkdir -p images && printf "$OK images/ directory ready\n"
[ -d "reports/sessions" ] || mkdir -p reports/sessions && printf "$OK reports/sessions/ ready\n"

echo ""

if [ $errors -eq 0 ]; then
  echo "=== All checks passed. Ready to demo. ==="
else
  echo "=== $errors issue(s) found — fix before demo. ==="
  exit 1
fi
echo ""
