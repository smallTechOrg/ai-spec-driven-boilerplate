# agent/eval_lint.py — exit 0 iff every EARS line is bound to a well-formed [@eval].
#   default (full, DEMO check 1): token present AND its path::case resolves to a real, COLLECTABLE test case.
#   --preflight (analyze pre-flight, before code exists): token present + shape + uniqueness only (no path.exists).
import argparse
import ast
import pathlib
import re
import sys

# An EARS *criterion* — not any prose sentence that happens to contain SHALL. It must START (after an
# optional list bullet/whitespace) with an EARS keyword AND contain SHALL.
EARS = re.compile(r"^\s*-?\s*(WHEN|WHILE|IF|WHERE)\b.*\bSHALL\b")
TOKEN = re.compile(r"\[@eval:\s*([^\]:]+)::([^\]]+)\]")


def _capability_files() -> list[pathlib.Path]:
    """Real capability specs only — skip `_`-prefixed files (e.g. `_template.md`), which are
    harness templates/partials carrying placeholder EARS lines, never a build's actual capability."""
    return [f for f in pathlib.Path("spec/capabilities").glob("*.md") if not f.name.startswith("_")]


def _defined_cases(path: pathlib.Path) -> set[str]:
    """Names pytest would actually COLLECT from the file — parsed via AST, never a substring scan."""
    cases: set[str] = set()
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return cases
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cases.add(node.name)                                   # base test function name
            for dec in node.decorator_list:                       # + explicit parametrize ids: foo[id]
                if (isinstance(dec, ast.Call) and getattr(dec.func, "attr", "") == "parametrize"):
                    for kw in dec.keywords:
                        if kw.arg == "ids" and isinstance(kw.value, (ast.List, ast.Tuple)):
                            for elt in kw.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    cases.add(f"{node.name}[{elt.value}]")
    return cases


# Refund-domain placeholders shipped in gate_eval.py / the Makefile — a build that left ANY of these is a
# half-applied edit that false-REDs.
_PLACEHOLDERS = ("WHEN asked about refund timing the system SHALL state 5 business days.",
                 "How long do refunds take?")


def _ears_lines() -> list[str]:
    """The criterion PROSE of every EARS line — with the trailing `[@eval: path::case]` token STRIPPED."""
    out = []
    for f in _capability_files():
        for ln in f.read_text().splitlines():
            if EARS.search(ln):
                out.append(re.sub(r"\s*\[@eval:[^\]]*\]", "", ln).strip(" -"))
    return out


def _gate_eval_sync(ears: list[str]) -> list[str]:
    """Full mode only: gate_eval.CRITERION must be a real EARS line in the spec (not the refund placeholder)."""
    probs = []
    try:
        from . import gate_eval                                   # the constants under test
    except Exception:                                             # gate_eval not generated yet / import error
        return probs
    crit = getattr(gate_eval, "CRITERION", "").strip()
    if crit in _PLACEHOLDERS:
        probs.append("agent/gate_eval.py CRITERION is still the refund placeholder — set it from the P1 EARS line")
    elif crit and crit not in {e.strip() for e in ears}:
        probs.append(f"agent/gate_eval.py CRITERION does not match any EARS line in spec/capabilities/* — Makefile GOAL and gate_eval CRITERION must trace to the SAME P1 line: {crit!r}")
    return probs


def main(preflight: bool = False) -> int:
    problems, seen = [], {}
    for f in _capability_files():
        lines = f.read_text().splitlines()
        for i, ln in enumerate(lines):
            if not EARS.search(ln):
                continue
            window = ln + ("\n" + lines[i + 1] if i + 1 < len(lines) else "")
            m = TOKEN.search(window)
            if not m:
                problems.append(f"{f}:{i+1}  EARS line has no [@eval] token")
                continue
            path, case = pathlib.Path(m.group(1).strip()), m.group(2).strip()
            ref = f"{path}::{case}"
            if ref in seen:                          # uniqueness: two EARS lines can't share one case
                problems.append(f"{f}:{i+1}  [@eval] duplicates {seen[ref]}: {ref}")
            seen[ref] = f"{f}:{i+1}"
            if preflight:                            # shape already validated by TOKEN; stop before file I/O
                continue
            if not path.exists():
                problems.append(f"{f}:{i+1}  [@eval] unresolved (no file): {ref}")
                continue
            if case not in _defined_cases(path):     # EXACT match — never substring
                problems.append(f"{f}:{i+1}  [@eval] unresolved (no collectable case `{case}`): {ref}")
    if not preflight:                                # gate mode: the rubric must trace to a real P1 EARS line
        problems += _gate_eval_sync(_ears_lines())
    for p in problems:
        print(f"EVAL-LINT FAIL{' (preflight)' if preflight else ''}: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--preflight", action="store_true")
    sys.exit(main(a.parse_args().preflight))
