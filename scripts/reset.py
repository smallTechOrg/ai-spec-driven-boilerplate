#!/usr/bin/env python3
"""Reset the repo to a clean boilerplate state for a new build.

Wipes all project-generated output: src/, tests/, migrations, lockfile,
virtualenv, and logs. Restores the seven product-spec docs (spec/*.md) to
their committed placeholder state, and clears the live coordination scratch
(logs/PLAN.md). The harness/ method is untouched.

Safe to run between workshop phases or before starting a fresh build.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# The seven product-spec docs (spec/ holds exactly these — see harness/layout.md).
# Reset restores each to its committed placeholder template state.
SPEC_DOCS = [
    "vision.md",
    "architecture.md",
    "data-model.md",
    "api.md",
    "ui.md",
    "agent-graph.md",
    "delivery-plan.md",
]


def confirm(prompt: str) -> bool:
    try:
        return input(f"{prompt} [y/N] ").strip().lower() == "y"
    except (EOFError, KeyboardInterrupt):
        return False


def remove(path: Path) -> None:
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f"  removed  {path.relative_to(ROOT)}")
    else:
        print(f"  skip     {path.relative_to(ROOT)}  (not found)")


def restore_from_git(rel: str) -> None:
    """Restore a tracked file to its committed (placeholder) state via git."""
    path = ROOT / rel
    result = subprocess.run(
        ["git", "checkout", "HEAD", "--", rel],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"  restored {rel}  (placeholder)")
    else:
        # Untracked or no committed baseline — leave as-is rather than guess.
        note = "not tracked" if not path.exists() else "no committed baseline"
        print(f"  skip     {rel}  ({note})")


print()
print("=== SDD Agent Harness — Reset to Boilerplate ===")
print()
print("This will remove:")
print("  src/         application code")
print("  tests/       test suite")
print("  alembic/     migrations")
print("  pyproject.toml, uv.lock, .venv/")
print("  logs/PLAN.md (live per-phase coordination scratch)")
print("  logs/sessions/*, logs/runtime/*, logs/analysis/*")
print()
print("And reset to placeholder state:")
print("  spec/*.md    the seven product-spec docs")
print()

if not confirm("Proceed?"):
    print("Aborted.")
    sys.exit(0)

print()
print("Cleaning...")

# Generated project code
for p in ["src", "tests", "alembic", "pyproject.toml", "uv.lock", ".venv"]:
    remove(ROOT / p)

# Live per-phase coordination scratch (ephemeral — rewritten by the planner each phase)
remove(ROOT / "logs" / "PLAN.md")

# The seven product-spec docs — restore each to its committed placeholder state
for doc in SPEC_DOCS:
    restore_from_git(f"spec/{doc}")

# Logs (keep folder structure, wipe contents)
for subdir in ["sessions", "runtime", "analysis"]:
    log_dir = ROOT / "logs" / subdir
    log_dir.mkdir(parents=True, exist_ok=True)
    for f in log_dir.iterdir():
        if f.name != ".gitkeep":
            remove(f)
    print(f"  cleared  logs/{subdir}/")

print()
print("=== Reset complete. Repo is back to boilerplate state. ===")
print()
print("Next steps:")
print("  git checkout -b feat/your-agent-name")
print("  claude")
print("  /build")
print()
