"""Deterministic verifier for candidate agent responses.

This starter verifier performs simple checks:
- Looks for common secret patterns
- Ensures the response includes a unified diff when expected
- Optionally runs formatters/linters if available (flake8)

Return format: {"verdict": "PASS"|"FAIL", "issues": [...], "confidence": 0.0-1.0}
"""
from __future__ import annotations

import re
import json
import subprocess
from typing import List, Dict, Any


SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"(?:s|S)ecret|password|passwd|token", re.IGNORECASE),
    re.compile(r"-----BEGIN (RSA|OPENSSH|PRIVATE) KEY-----"),
]


def find_secrets(text: str) -> List[str]:
    issues = []
    for p in SECRET_PATTERNS:
        if p.search(text):
            issues.append(f"Potential secret match: {p.pattern}")
    return issues


def looks_like_diff(text: str) -> bool:
    return text.strip().startswith("diff --git") or text.strip().startswith("--- a/")


def run_flake8_on_patch(patch_text: str) -> List[str]:
    """Try to extract Python files from a unified diff and run flake8 if available.
    Returns a list of reported issues (strings). If flake8 is not installed, returns [].
    """
    try:
        proc = subprocess.run(["flake8", "--version"], capture_output=True, text=True)
        if proc.returncode != 0 and not proc.stdout:
            return []
    except FileNotFoundError:
        return []

    # Naive extraction: find file blocks and write temp files not implemented here.
    # For now, return empty to avoid side effects.
    return []


def verify_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Verify a candidate dictionary (e.g., from generate_ensemble)."""
    issues: List[str] = []
    messages = candidate.get("messages", [])
    full_text = "\n".join(m.get("text", "") for m in messages)

    issues.extend(find_secrets(full_text))

    if "patch" in candidate:
        if not looks_like_diff(candidate.get("patch", "")):
            issues.append("Expected a unified diff patch but none found.")
        issues.extend(run_flake8_on_patch(candidate.get("patch", "")))

    verdict = "PASS" if not issues else "FAIL"
    confidence = 1.0 if verdict == "PASS" else 0.6
    return {"verdict": verdict, "issues": issues, "confidence": confidence}


def run_cli():
    import argparse

    parser = argparse.ArgumentParser(description="Run deterministic verifier on a JSON candidate file or stdin")
    parser.add_argument("file", nargs="?", help="JSON file with candidate or - for stdin", default="-")
    args = parser.parse_args()

    if args.file == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.file, "r") as f:
            data = json.load(f)

    out = verify_candidate(data)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    import sys
    run_cli()
